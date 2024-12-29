import contextlib
import logging
import math
import os
import select
import shlex
import shutil
import signal
import subprocess
import threading
import time
import timeit
import weakref
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import IO, Any

from clan_cli.async_run import get_async_ctx, is_async_cancelled
from clan_cli.colors import Color
from clan_cli.custom_logger import print_trace
from clan_cli.errors import ClanCmdError, ClanError, CmdOut, indent_command

cmdlog = logging.getLogger(__name__)


class ClanCmdTimeoutError(ClanError):
    timeout: float

    def __init__(
        self,
        msg: str | None = None,
        *,
        description: str | None = None,
        location: str | None = None,
        timeout: float,
    ) -> None:
        self.timeout = timeout
        super().__init__(msg, description=description, location=location)


class Log(Enum):
    NONE = 0
    STDERR = 1
    STDOUT = 2
    BOTH = 3


@dataclass
class MsgColor:
    stderr: Color | None = None
    stdout: Color | None = None


def handle_io(
    process: subprocess.Popen,
    log: Log,
    *,
    prefix: str | None,
    input_bytes: bytes | None,
    stdout: IO[bytes] | None,
    stderr: IO[bytes] | None,
    timeout: float = math.inf,
    msg_color: MsgColor | None = None,
) -> tuple[str, str]:
    rlist = [
        process.stdout,
        process.stderr,
    ]  # rlist is a list of file descriptors to be monitored for read events
    wlist = (
        [process.stdin] if input_bytes is not None else []
    )  # wlist is a list of file descriptors to be monitored for write events
    stdout_buf = b""
    stderr_buf = b""
    start = time.time()

    # Function to handle file descriptors
    def handle_fd(fd: IO[Any] | None, readlist: list[IO[Any]]) -> bytes:
        if fd and fd in readlist:
            read = os.read(fd.fileno(), 4096)
            if len(read) != 0:
                return read
            rlist.remove(fd)
        return b""

    # Extra information passed to the logger
    stdout_extra = {}
    stderr_extra = {}
    if prefix:
        stdout_extra["command_prefix"] = prefix
        stderr_extra["command_prefix"] = prefix
    if msg_color and msg_color.stderr:
        stdout_extra["color"] = msg_color.stderr.value
    if msg_color and msg_color.stdout:
        stderr_extra["color"] = msg_color.stdout.value

    # Loop until no more data is available
    while len(rlist) != 0 or len(wlist) != 0:
        # Check if the command has timed out
        if time.time() - start > timeout:
            msg = f"Command timed out after {timeout} seconds"
            description = prefix
            raise ClanCmdTimeoutError(msg=msg, description=description, timeout=timeout)

        # Check if the command has been cancelled
        if is_async_cancelled():
            cmdlog.warning("Command cancelled", extra=stderr_extra)

            # Terminate process
            break

        # Wait for data to be available
        readlist, writelist, _ = select.select(rlist, wlist, [], 0.1)
        if len(readlist) == 0 and len(writelist) == 0:
            if process.poll() is None:
                continue
            # Process has exited
            break

        #
        # Process stdout
        #
        ret = handle_fd(process.stdout, readlist)

        # If Log.STDOUT is set, log the stdout output
        if ret and log in [Log.STDOUT, Log.BOTH]:
            lines = ret.decode("utf-8", "replace").rstrip("\n").rstrip().split("\n")
            for line in lines:
                cmdlog.info(line, extra=stdout_extra)

        # If stdout file is set, stream the stdout output
        if ret and stdout:
            stdout.write(ret)
            stdout.flush()
        stdout_buf += ret

        #
        # Process stderr
        #
        ret = handle_fd(process.stderr, readlist)

        # If Log.STDERR is set, log the stderr output
        if ret and log in [Log.STDERR, Log.BOTH]:
            lines = ret.decode("utf-8", "replace").rstrip("\n").rstrip().split("\n")
            for line in lines:
                cmdlog.info(line, extra=stderr_extra)

        # If stderr file is set, stream the stderr output
        if ret and stderr:
            stderr.write(ret)
            stderr.flush()
        stderr_buf += ret

        #
        # Process stdin
        #
        if process.stdin in writelist:
            if input_bytes:
                try:
                    assert process.stdin is not None
                    written = os.write(process.stdin.fileno(), input_bytes)
                except BrokenPipeError:
                    wlist.remove(process.stdin)
                else:
                    input_bytes = input_bytes[written:]
                    if len(input_bytes) == 0:
                        wlist.remove(process.stdin)
                    process.stdin.flush()
                    process.stdin.close()
            else:
                wlist.remove(process.stdin)
    return stdout_buf.decode("utf-8", "replace"), stderr_buf.decode("utf-8", "replace")


@contextmanager
def terminate_process_group(process: subprocess.Popen) -> Iterator[None]:
    try:
        process_group = os.getpgid(process.pid)
    except ProcessLookupError:
        return
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
        self.lock = threading.Lock()
        weakref.finalize(self, self.table_print)

    def table_print(self) -> None:
        with self.lock:
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
        with self.lock:
            if cmd in self.table:
                self.table[cmd] += time
            else:
                self.table[cmd] = time


TIME_TABLE = None
if os.environ.get("CLAN_CLI_PERF"):
    TIME_TABLE = TimeTable()


@dataclass
class RunOpts:
    input: bytes | None = None
    stdout: IO[bytes] | None = None
    stderr: IO[bytes] | None = None
    env: dict[str, str] | None = None
    cwd: Path | None = None
    log: Log = Log.STDERR
    prefix: str | None = None
    msg_color: MsgColor | None = None
    check: bool = True
    error_msg: str | None = None
    needs_user_terminal: bool = False
    timeout: float = math.inf
    shell: bool = False
    # Some commands require sudo
    requires_root_perm: bool = False
    # Ask for sudo password in a graphical way.
    # This is needed for GUI applications
    graphical_perm: bool = False


def cmd_with_root(cmd: list[str], graphical: bool = False) -> list[str]:
    """
    This function returns a wrapped command that will be run with root permissions.
    It will use sudo if graphical is False, otherwise it will use run0 or pkexec.
    """
    if os.geteuid() == 0:
        return cmd

    # Decide permission handler
    if graphical:
        # TODO(mic92): figure out how to use run0
        # if shutil.which("run0") is not None:
        #     perm_prefix = "run0"
        if shutil.which("pkexec") is not None:
            return ["pkexec", *cmd]
        description = (
            "pkexec is required to launch root commands with graphical permissions"
        )
        msg = "Missing graphical permission handler"
        raise ClanError(msg, description=description)
    if shutil.which("sudo") is None:
        msg = "sudo is required to run this command as a non-root user"
        raise ClanError(msg)

    return ["sudo", *cmd]


def run(
    cmd: list[str],
    options: RunOpts | None = None,
) -> CmdOut:
    if options is None:
        options = RunOpts()
    if options.cwd is None:
        options.cwd = Path.cwd()

    async_ctx = get_async_ctx()
    # Fill in the options from the thread-local data
    # if they are not set in the options
    if async_ctx:
        if options.prefix is None:
            options.prefix = async_ctx.prefix
        if options.stdout is None:
            options.stdout = async_ctx.stdout
        if options.stderr is None:
            options.stderr = async_ctx.stderr

    if options.requires_root_perm:
        cmd = cmd_with_root(cmd, options.graphical_perm)

    if options.input:
        if any(not ch.isprintable() for ch in options.input.decode("ascii", "replace")):
            filtered_input = "<<binary_blob>>"
        else:
            filtered_input = options.input.decode("ascii", "replace")
        print_trace(
            f"echo '{filtered_input}' | {indent_command(cmd)}",
            cmdlog,
            options.prefix,
        )
    elif cmdlog.isEnabledFor(logging.DEBUG):
        print_trace(f"{indent_command(cmd)}", cmdlog, options.prefix)

    start = timeit.default_timer()
    with ExitStack() as stack:
        stdin = subprocess.PIPE if options.input is not None else None
        process = stack.enter_context(
            subprocess.Popen(
                cmd,
                cwd=str(options.cwd),
                env=options.env,
                stdin=stdin,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=not options.needs_user_terminal,
                shell=options.shell,
            )
        )

        if options.needs_user_terminal:
            # we didn't allocate a new session, so we can't terminate the process group
            stack.enter_context(terminate_process(process))
        else:
            stack.enter_context(terminate_process_group(process))

        stdout_buf, stderr_buf = handle_io(
            process,
            options.log,
            prefix=options.prefix,
            msg_color=options.msg_color,
            timeout=options.timeout,
            input_bytes=options.input,
            stdout=options.stdout,
            stderr=options.stderr,
        )
        if not is_async_cancelled():
            process.wait()

    global TIME_TABLE
    if TIME_TABLE:
        TIME_TABLE.add(shlex.join(cmd), timeit.default_timer() - start)

    # Wait for the subprocess to finish
    cmd_out = CmdOut(
        stdout=stdout_buf,
        stderr=stderr_buf,
        cwd=options.cwd,
        env=options.env,
        command_list=cmd,
        returncode=process.returncode,
        msg=options.error_msg,
    )

    if options.check and process.returncode != 0:
        err = ClanCmdError(cmd_out)
        err.msg = "Command has been cancelled"
        raise err

    return cmd_out


def run_no_stdout(
    cmd: list[str],
    opts: RunOpts | None = None,
) -> CmdOut:
    """
    Like run, but automatically suppresses all output, if not in DEBUG log level.
    If in DEBUG log level the stdout of commands will be shown.
    """
    if opts is None:
        opts = RunOpts()

    if cmdlog.isEnabledFor(logging.DEBUG):
        opts.log = opts.log if opts.log.value > Log.STDERR.value else Log.STDERR

    return run(
        cmd,
        opts,
    )


# type: ignore
