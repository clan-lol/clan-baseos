import logging
import os
import shlex

from clan_app import main
from clan_cli.custom_logger import get_callers

log = logging.getLogger(__name__)


def print_trace(msg: str) -> None:
    trace_depth = int(os.environ.get("TRACE_DEPTH", "0"))
    callers = get_callers(2, 2 + trace_depth)

    if "run_no_stdout" in callers[0]:
        callers = get_callers(3, 3 + trace_depth)
    callers_str = "\n".join(f"{i + 1}: {caller}" for i, caller in enumerate(callers))
    log.debug(f"{msg} \nCallers: \n{callers_str}")


def run(args: list[str]) -> None:
    cmd = shlex.join(["clan", *args])
    print_trace(f"$ {cmd}")
    main(args)
