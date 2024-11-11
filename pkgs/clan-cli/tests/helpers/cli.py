import argparse
import logging
import os
import shlex

from clan_cli import create_parser
from clan_cli.custom_logger import get_callers

log = logging.getLogger(__name__)


def print_trace(msg: str) -> None:
    trace_depth = int(os.environ.get("TRACE_DEPTH", "0"))
    callers = get_callers(2, 2 + trace_depth)

    if "run_no_stdout" in callers[0]:
        callers = get_callers(3, 3 + trace_depth)
    callers_str = "\n".join(f"{i+1}: {caller}" for i, caller in enumerate(callers))
    log.debug(f"{msg} \nCallers: \n{callers_str}")


def run(args: list[str]) -> argparse.Namespace:
    parser = create_parser(prog="clan")
    parsed = parser.parse_args(args)
    cmd = shlex.join(["clan", *args])

    print_trace(f"$ {cmd}")
    if hasattr(parsed, "func"):
        parsed.func(parsed)
    return parsed
