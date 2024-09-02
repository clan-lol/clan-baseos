import dataclasses
import logging
import multiprocessing as mp
import os
import signal
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# Kill the new process and all its children by sending a SIGTERM signal to the process group
def _kill_group(proc: mp.Process) -> None:
    pid = proc.pid
    if proc.is_alive() and pid:
        os.killpg(pid, signal.SIGTERM)
    else:
        log.warning(f"Process '{proc.name}' with pid '{pid}' is already dead")


@dataclasses.dataclass(frozen=True)
class MPProcess:
    name: str
    proc: mp.Process
    out_file: Path

    # Kill the new process and all its children by sending a SIGTERM signal to the process group
    def kill_group(self) -> None:
        _kill_group(proc=self.proc)


def _set_proc_name(name: str) -> None:
    if sys.platform != "linux":
        return
    import ctypes

    # Define the prctl function with the appropriate arguments and return type
    libc = ctypes.CDLL("libc.so.6")
    prctl = libc.prctl
    prctl.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    prctl.restype = ctypes.c_int

    # Set the process name to "my_process"
    prctl(15, name.encode(), 0, 0, 0)


def _init_proc(
    func: Callable,
    out_file: Path,
    proc_name: str,
    on_except: Callable[[Exception, mp.process.BaseProcess], None] | None,
    **kwargs: Any,
) -> None:
    # Create a new process group
    os.setsid()

    # Open stdout and stderr
    with out_file.open("w") as out_fd:
        os.dup2(out_fd.fileno(), sys.stdout.fileno())
        os.dup2(out_fd.fileno(), sys.stderr.fileno())

    # Print some information
    pid = os.getpid()
    gpid = os.getpgid(pid=pid)

    # Set the process name
    _set_proc_name(proc_name)

    # Close stdin
    sys.stdin.close()

    linebreak = "=" * 5
    # Execute the main function
    print(linebreak + f" {func.__name__}:{pid} " + linebreak, file=sys.stderr)
    try:
        func(**kwargs)
    except Exception as ex:
        traceback.print_exc()
        if on_except is not None:
            on_except(ex, mp.current_process())

            # Kill the new process and all its children by sending a SIGTERM signal to the process group
            pid = os.getpid()
            gpid = os.getpgid(pid=pid)
            print(f"Killing process group pid={pid} gpid={gpid}", file=sys.stderr)
            os.killpg(gpid, signal.SIGTERM)
        sys.exit(1)
    # Don't use a finally block here, because we want the exitcode to be set to
    # 0 if the function returns normally


def spawn(
    *,
    out_file: Path,
    on_except: Callable[[Exception, mp.process.BaseProcess], None] | None,
    func: Callable,
    **kwargs: Any,
) -> MPProcess:
    # Decouple the process from the parent
    if mp.get_start_method(allow_none=True) is None:
        mp.set_start_method(method="forkserver")

    # Set names
    proc_name = f"MPExec:{func.__name__}"

    # Start the process
    proc = mp.Process(
        target=_init_proc,
        args=(func, out_file, proc_name, on_except),
        name=proc_name,
        kwargs=kwargs,
    )
    proc.start()

    # Return the process
    mp_proc = MPProcess(name=proc_name, proc=proc, out_file=out_file)

    return mp_proc
