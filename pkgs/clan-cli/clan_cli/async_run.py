import logging
import threading
import time
import types
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import IO, Any, Generic, ParamSpec, TypeVar

from clan_cli.errors import ClanError

log = logging.getLogger(__name__)

# Why did we create a custom AsyncRuntime instead of using asyncio?
#
# The AsyncRuntime class allows us to run functions in separate threads for asynchronous
# execution without requiring the use of the "async" keyword. By using this approach,
# functions can gracefully handle cancellation by checking if get_async_ctx().cancel is True.
#
# There was some resistance to using asyncio, partly due to challenges we faced when
# implementing it in our first web interface. Threads felt simpler and more familiar
# for our use case.
#
# That said, asyncio is generally more efficient because it uses non-blocking I/O
# and avoids issues with Python's Global Interpreter Lock (GIL), which can limit the
# performance of threads in CPU-heavy workloads.
#
# Using threads works well for us because most of the time is spent waiting for commands
# or external processes to finish, rather than performing heavy computing tasks.
#
# Note: Starting with Python 3.14, the GIL can be disabled to enable true parallelism.
# However, disabling the GIL introduces a 10-40% performance cost for Python code
# due to the overhead of additional locking.

# Define generics for return type and call signature
R = TypeVar("R")  # Return type of the callable
P = ParamSpec("P")  # Parameters of the callable


@dataclass
class AsyncResult(Generic[R]):
    _result: R | Exception

    @property
    def error(self) -> Exception | None:
        """
        Returns an error if the callable raised an exception.
        """
        if isinstance(self._result, Exception):
            return self._result
        return None

    @property
    def result(self) -> R:
        """
        Unwraps and returns the result if no exception occurred.
        Raises the exception otherwise.
        """
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


@dataclass
class AsyncContext:
    """
    This class stores thread-local data.
    """

    prefix: str | None = None  # prefix for logging
    stdout: IO[bytes] | None = None  # stdout of subprocesses
    stderr: IO[bytes] | None = None  # stderr of subprocesses
    cancel: bool = False  # Used to signal cancellation of task


@dataclass
class AsyncOpts:
    """
    Options for the async_run function.
    """

    tid: str | None = None
    check: bool = True
    async_ctx: AsyncContext = field(default_factory=AsyncContext)


ASYNC_CTX_THREAD_LOCAL = threading.local()


def is_async_cancelled() -> bool:
    """
    Check if the current task has been cancelled.
    """
    return get_async_ctx().cancel


def get_async_ctx() -> AsyncContext:
    """
    Retrieve the current AsyncContext, creating a new one if none exists.
    """
    global ASYNC_CTX_THREAD_LOCAL

    if not hasattr(ASYNC_CTX_THREAD_LOCAL, "async_ctx"):
        ASYNC_CTX_THREAD_LOCAL.async_ctx = AsyncContext()
    return ASYNC_CTX_THREAD_LOCAL.async_ctx


def set_async_ctx(ctx: AsyncContext) -> None:
    global ASYNC_CTX_THREAD_LOCAL
    ASYNC_CTX_THREAD_LOCAL.async_ctx = ctx


class AsyncThread(threading.Thread, Generic[P, R]):
    function: Callable[P, R]
    args: Any
    kwargs: Any
    result: AsyncResult[R] | None
    finished: bool
    condition: threading.Condition
    async_opts: AsyncOpts

    def __init__(
        self,
        async_opts: AsyncOpts,
        condition: threading.Condition,
        function: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """
        A threaded wrapper for running a function asynchronously.
        """
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.result: AsyncResult[R] | None = None  # Store the result or exception
        self.finished = False  # Set to True after the thread finishes execution
        self.condition = condition  # Shared condition variable
        self.async_opts = async_opts

    def run(self) -> None:
        """
        Run the function in a separate thread.
        """
        try:
            set_async_ctx(self.async_opts.async_ctx)
            self.result = AsyncResult(_result=self.function(*self.args, **self.kwargs))
        except Exception as ex:
            self.result = AsyncResult(_result=ex)
        finally:
            self.finished = True
            # Acquire the condition lock before notifying
            with self.condition:
                self.condition.notify_all()  # Notify waiting threads that this thread is done


@dataclass
class AsyncFuture(Generic[R]):
    _tid: str
    _runtime: "AsyncRuntime"

    def wait(self) -> AsyncResult[R]:
        """
        Wait for the task to finish.
        """
        if self._tid not in self._runtime.tasks:
            msg = f"No task with the name '{self._tid}' exists."
            raise ClanError(msg)

        thread = self._runtime.tasks[self._tid]
        thread.join()
        result = self.get_result()
        if result is None:
            msg = f"Task '{self._tid}' unexpectedly returned None."
            raise ClanError(msg)
        return result

    def get_result(self) -> AsyncResult[R] | None:
        """
        Retrieve the result of a finished task and remove it from the task list.
        """
        if self._tid not in self._runtime.tasks:
            msg = f"No task with the name '{self._tid}' exists."
            raise ClanError(msg)

        thread = self._runtime.tasks[self._tid]

        if not thread.finished:
            return None

        # Remove the task after retrieving the result
        result = thread.result
        del self._runtime.tasks[self._tid]

        if result is None:
            msg = f"The result for task '{self._tid}' is unexpectedly None."
            raise ClanError(msg)

        return result


@dataclass
class AsyncRuntime:
    tasks: dict[str, AsyncThread[Any, Any]] = field(default_factory=dict)
    condition: threading.Condition = field(default_factory=threading.Condition)

    def async_run(
        self,
        opts: AsyncOpts | None,
        function: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> AsyncFuture[R]:
        """
        Run the given function asynchronously in a thread with a specific name and arguments.
        The function's static typing is preserved.
        """
        if opts is None:
            opts = AsyncOpts()

        if opts.tid is None:
            opts.tid = uuid.uuid4().hex

        if opts.tid in self.tasks:
            msg = f"A task with the name '{opts.tid}' is already running."
            raise ClanError(msg)

        # Create and start the new AsyncThread
        thread = AsyncThread(opts, self.condition, function, *args, **kwargs)
        self.tasks[opts.tid] = thread
        thread.start()
        return AsyncFuture(opts.tid, self)

    def join_all(self) -> None:
        """
        Wait for all tasks to finish
        """
        with self.condition:
            while any(
                not task.finished for task in self.tasks.values()
            ):  # Check if any tasks are still running
                self.condition.wait()  # Wait until a thread signals completion

    def check_all(self) -> None:
        """
        Check if there where any errors
        """
        err_count = 0

        for name, task in self.tasks.items():
            if task.finished and task.async_opts.check:
                assert task.result is not None
                error = task.result.error
                if log.isEnabledFor(logging.DEBUG):
                    log.error(
                        f"failed with error: {error}",
                        extra={"command_prefix": name},
                        exc_info=error,
                    )
                else:
                    log.error(
                        f"failed with error: {error}", extra={"command_prefix": name}
                    )
                err_count += 1

        if err_count > 0:
            msg = f"{err_count} hosts failed with an error. Check the logs above"
            raise ClanError(msg)

    def __enter__(self) -> "AsyncRuntime":
        """
        Enter the runtime context related to this object.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        """
        Exit the runtime context related to this object.
        Sets async_ctx.cancel to True to signal cancellation.
        """
        for name, task in self.tasks.items():
            if not task.finished:
                task.async_opts.async_ctx.cancel = True
                log.debug(f"Canceling task {name}")


# Example usage
if __name__ == "__main__":
    runtime = AsyncRuntime()

    def add(a: int, b: int) -> int:
        return a + b

    def concatenate(a: str, b: str) -> str:
        time.sleep(1)
        msg = "Hello World"
        raise ClanError(msg)

    with runtime:
        p1 = runtime.async_run(None, add, 1, 2)
        p2 = runtime.async_run(None, concatenate, "Hello ", "World")

    add_result = p1.wait()
    print(add_result.result)  # Output: 3
    concat_result = p2.wait()
    print(concat_result.error)  # Output: Hello World
