import contextlib
import logging
import os
import select
import shlex
import signal
import subprocess
import sys
import timeit
import weakref
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from enum import Enum
from pathlib import Path
from typing import IO, Any

from clan_cli.errors import ClanError, indent_command

from .custom_logger import get_callers
from .errors import ClanCmdError, CmdOut

logger = logging.getLogger(__name__)


class Log(Enum):
    STDERR = 1
    STDOUT = 2
    BOTH = 3
    NONE = 4


def handle_output(process: subprocess.Popen, log: Log) -> tuple[str, str]:
    rlist = [process.stdout, process.stderr]
    stdout_buf = b""
    stderr_buf = b""

    while len(rlist) != 0:
        readlist, _, _ = select.select(rlist, [], [], 0.1)
        if len(readlist) == 0:  # timeout in select
            if process.poll() is None:
                continue
            # Process has exited
            break

        def handle_fd(fd: IO[Any] | None, readlist: list[IO[Any]]) -> bytes:
            if fd and fd in readlist:
                read = os.read(fd.fileno(), 4096)
                if len(read) != 0:
                    return read
                rlist.remove(fd)
            return b""

        ret = handle_fd(process.stdout, readlist)
        if ret and log in [Log.STDOUT, Log.BOTH]:
            sys.stdout.buffer.write(ret)
            sys.stdout.flush()

        stdout_buf += ret
        ret = handle_fd(process.stderr, readlist)

        if ret and log in [Log.STDERR, Log.BOTH]:
            sys.stderr.buffer.write(ret)
            sys.stderr.flush()
        stderr_buf += ret
    return stdout_buf.decode("utf-8", "replace"), stderr_buf.decode("utf-8", "replace")


@contextmanager
def terminate_process_group(process: subprocess.Popen) -> Iterator[None]:
    process_group = os.getpgid(process.pid)
    if process_group == os.getpgid(os.getpid()):
        msg = "Bug! Refusing to terminate the current process group"
        raise ClanError(msg)
    try:
        yield
    finally:
        try:
            os.killpg(process_group, signal.SIGTERM)
            try:
                with contextlib.suppress(subprocess.TimeoutExpired):
                    # give the process time to terminate
                    process.wait(3)
            finally:
                os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:  # process already terminated
            pass


@contextmanager
def terminate_process(process: subprocess.Popen) -> Iterator[None]:
    try:
        yield
    finally:
        try:
            process.terminate()
            try:
                with contextlib.suppress(subprocess.TimeoutExpired):
                    # give the process time to terminate
                    process.wait(3)
            finally:
                process.kill()
        except ProcessLookupError:
            pass


class TimeTable:
    """
    This class is used to store the time taken by each command
    and print it at the end of the program if env CLAN_CLI_PERF=1 is set.
    """

    def __init__(self) -> None:
        self.table: dict[str, float] = {}
        weakref.finalize(self, self.table_print)

    def table_print(self) -> None:
        print("======== CMD TIMETABLE ========")

        # Sort the table by time in descending order
        sorted_table = sorted(
            self.table.items(), key=lambda item: item[1], reverse=True
        )

        for k, v in sorted_table:
            # Check if timedelta is greater than 1 second
            if v > 1:
                # Print in red
                print(f"\033[91mTook {v}s\033[0m for command: '{k}'")
            else:
                # Print in default color
                print(f"Took {v} for command: '{k}'")

    def add(self, cmd: str, time: float) -> None:
        if cmd in self.table:
            self.table[cmd] += time
        else:
            self.table[cmd] = time


TIME_TABLE = None
if os.environ.get("CLAN_CLI_PERF"):
    TIME_TABLE = TimeTable()


def run(
    cmd: list[str],
    *,
    input: bytes | None = None,  # noqa: A002
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    log: Log = Log.STDERR,
    check: bool = True,
    error_msg: str | None = None,
    needs_user_terminal: bool = False,
) -> CmdOut:
    if cwd is None:
        cwd = Path.cwd()

    def print_trace(msg: str) -> None:
        trace_depth = int(os.environ.get("TRACE_DEPTH", "0"))
        callers = get_callers(3, 4 + trace_depth)

        if "run_no_stdout" in callers[0]:
            callers = callers[1:]
        else:
            callers.pop()

        if len(callers) == 1:
            callers_str = f"Caller: {callers[0]}\n"
        else:
            callers_str = "\n".join(
                f"{i+1}: {caller}" for i, caller in enumerate(callers)
            )
            callers_str = f"Callers:\n{callers_str}"
        logger.debug(f"{msg} \n{callers_str}")

    if input:
        print_trace(
            f"$: echo '{input.decode('utf-8', 'replace')}' | {indent_command(cmd)}"
        )
    elif logger.isEnabledFor(logging.DEBUG):
        print_trace(f"$: {indent_command(cmd)}")

    start = timeit.default_timer()
    with ExitStack() as stack:
        process = stack.enter_context(
            subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=not needs_user_terminal,
            )
        )

        if needs_user_terminal:
            # we didn't allocat a new session, so we can't terminate the process group
            stack.enter_context(terminate_process(process))
        else:
            stack.enter_context(terminate_process_group(process))

        stdout_buf, stderr_buf = handle_output(process, log)

        if input:
            process.communicate(input)

    global TIME_TABLE
    if TIME_TABLE:
        TIME_TABLE.add(shlex.join(cmd), start - timeit.default_timer())

    # Wait for the subprocess to finish
    cmd_out = CmdOut(
        stdout=stdout_buf,
        stderr=stderr_buf,
        cwd=cwd,
        env=env,
        command_list=cmd,
        returncode=process.returncode,
        msg=error_msg,
    )

    if check and process.returncode != 0:
        raise ClanCmdError(cmd_out)

    return cmd_out


def run_no_stdout(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    log: Log = Log.STDERR,
    check: bool = True,
    error_msg: str | None = None,
    needs_user_terminal: bool = False,
) -> CmdOut:
    """
    Like run, but automatically suppresses stdout, if not in DEBUG log level.
    If in DEBUG log level the stdout of commands will be shown.
    """
    if cwd is None:
        cwd = Path.cwd()
    if logger.isEnabledFor(logging.DEBUG):
        return run(cmd, env=env, log=log, check=check, error_msg=error_msg)
    log = Log.NONE
    return run(
        cmd,
        env=env,
        log=log,
        check=check,
        error_msg=error_msg,
        needs_user_terminal=needs_user_terminal,
    )
