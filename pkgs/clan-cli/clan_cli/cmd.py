import datetime
import logging
import os
import select
import shlex
import subprocess
import sys
import weakref
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import IO, Any

from .custom_logger import get_caller
from .errors import ClanCmdError, CmdOut

glog = logging.getLogger(__name__)


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


class TimeTable:
    """
    This class is used to store the time taken by each command
    and print it at the end of the program if env PERF=1 is set.
    """

    def __init__(self) -> None:
        self.table: dict[str, timedelta] = {}
        weakref.finalize(self, self.table_print)

    def table_print(self) -> None:
        print("======== CMD TIMETABLE ========")

        # Sort the table by time in descending order
        sorted_table = sorted(
            self.table.items(), key=lambda item: item[1], reverse=True
        )

        for k, v in sorted_table:
            # Check if timedelta is greater than 1 second
            if v.total_seconds() > 1:
                # Print in red
                print(f"\033[91mTook {v}s\033[0m for command: '{k}'")
            else:
                # Print in default color
                print(f"Took {v} for command: '{k}'")

    def add(self, cmd: str, time: timedelta) -> None:
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
) -> CmdOut:
    if cwd is None:
        cwd = Path.cwd()
    if input:
        glog.debug(
            f"""$: echo "{input.decode('utf-8', 'replace')}" | {shlex.join(cmd)} \nCaller: {get_caller()}"""
        )
    else:
        glog.debug(f"$: {shlex.join(cmd)} \nCaller: {get_caller()}")
    tstart = datetime.datetime.now(tz=datetime.UTC)

    # Start the subprocess
    with subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        stdout_buf, stderr_buf = handle_output(process, log)

        if input:
            process.communicate(input)
        else:
            process.wait()
        tend = datetime.datetime.now(tz=datetime.UTC)

    global TIME_TABLE
    if TIME_TABLE:
        TIME_TABLE.add(shlex.join(cmd), tend - tstart)

    # Wait for the subprocess to finish
    cmd_out = CmdOut(
        stdout=stdout_buf,
        stderr=stderr_buf,
        cwd=cwd,
        command=shlex.join(cmd),
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
) -> CmdOut:
    """
    Like run, but automatically suppresses stdout, if not in DEBUG log level.
    If in DEBUG log level the stdout of commands will be shown.
    """
    if cwd is None:
        cwd = Path.cwd()
    if logging.getLogger(__name__.split(".")[0]).isEnabledFor(logging.DEBUG):
        return run(cmd, env=env, log=log, check=check, error_msg=error_msg)
    log = Log.NONE
    return run(cmd, env=env, log=log, check=check, error_msg=error_msg)
