import inspect
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from clan_cli.colors import AnsiColor, RgbColor, color_by_tuple

# https://no-color.org
DISABLE_COLOR = not sys.stderr.isatty() or os.environ.get("NO_COLOR", "") != ""


def _get_filepath(record: logging.LogRecord) -> Path:
    try:
        filepath = Path(record.pathname).resolve()
        filepath = Path("~", filepath.relative_to(Path.home()))
    except Exception:
        filepath = Path(record.pathname)
    return filepath


class PrefixFormatter(logging.Formatter):
    """
    print errors in red and warnings in yellow
    """

    def __init__(
        self, trace_prints: bool = False, default_prefix: str | None = None
    ) -> None:
        self.default_prefix = default_prefix
        self.trace_prints = trace_prints

        super().__init__()
        self.hostnames: list[str] = []
        self.hostname_color_offset = 1  # first host shouldn't get aggressive red

    def format(self, record: logging.LogRecord) -> str:
        filepath = _get_filepath(record)

        if record.levelno == logging.DEBUG:
            ansi_color_str = getattr(record, "stdout_color", None)
            if ansi_color_str is not None:
                ansi_color = json.loads(ansi_color_str)
            else:
                ansi_color = AnsiColor.BLUE.value
        elif record.levelno == logging.ERROR:
            ansi_color_str = getattr(record, "stderr_color", None)
            if ansi_color_str is not None:
                ansi_color = json.loads(ansi_color_str)
            else:
                ansi_color = AnsiColor.RED.value
        elif record.levelno == logging.WARNING:
            ansi_color = AnsiColor.YELLOW.value
        else:
            ansi_color = AnsiColor.DEFAULT.value

        command_prefix = getattr(record, "command_prefix", self.default_prefix)

        if DISABLE_COLOR:
            if command_prefix:
                format_str = f"[{command_prefix}] %(message)s"
            else:
                format_str = "%(message)s"
        elif command_prefix:
            prefix_color = self.hostname_colorcode(command_prefix)
            format_str = color_by_tuple(f"[{command_prefix}]", fg=prefix_color)
            format_str += color_by_tuple(" %(message)s", fg=ansi_color)
        else:
            format_str = color_by_tuple("%(message)s", fg=ansi_color)

        if self.trace_prints:
            format_str += f"\nSource: {filepath}:%(lineno)d::%(funcName)s\n"

        return logging.Formatter(format_str).format(record)

    def hostname_colorcode(self, hostname: str) -> tuple[int, int, int]:
        colorcodes = RgbColor.list_values()
        try:
            index = self.hostnames.index(hostname)
        except ValueError:
            self.hostnames += [hostname]
            index = self.hostnames.index(hostname)
        coloroffset = (index + self.hostname_color_offset) % len(colorcodes)
        colorcode = colorcodes[coloroffset]

        return colorcode


def get_callers(start: int = 2, end: int = 2) -> list[str]:
    """
    Get a list of caller information for a given range in the call stack.

    :param start: The starting position in the call stack (1 being directly above in the call stack).
    :param end: The end position in the call stack.
    :return: A list of strings, each containing the file, line number, and function of the caller.
    """

    frame = inspect.currentframe()
    if frame is None:
        return ["unknown"]

    callers = []
    current_frame = frame.f_back  # start from the caller of this function

    # Skip `start - 1` frames.
    for _ in range(start - 1):
        if current_frame is not None:
            current_frame = current_frame.f_back
        else:
            # If there aren't enough frames, return what we have as "unknown".
            return ["unknown"] * (end - start + 1)

    # Collect frame info until the `end` position.
    for _ in range(end - start + 1):
        if current_frame is not None:
            frame_info = inspect.getframeinfo(current_frame)

            try:
                filepath = Path(frame_info.filename).resolve()
                filepath = Path("~", filepath.relative_to(Path.home()))
            except Exception:
                filepath = Path(frame_info.filename)

            ret = f"{filepath}:{frame_info.lineno}::{frame_info.function}"
            callers.append(ret)
            current_frame = current_frame.f_back
        else:
            # If there are no more frames but we haven't reached `end`, append "unknown".
            callers.append("unknown")

    return callers


def print_trace(msg: str, logger: logging.Logger, prefix: str | None) -> None:
    trace_depth = int(os.environ.get("TRACE_DEPTH", "0"))
    callers = get_callers(3, 4 + trace_depth)

    if "run_no_stdout" in callers[0]:
        callers = callers[1:]
    else:
        callers.pop()

    if len(callers) == 1:
        callers_str = f"Caller: {callers[0]}\n"
    else:
        callers_str = "\n".join(f"{i+1}: {caller}" for i, caller in enumerate(callers))
        callers_str = f"Callers:\n{callers_str}"
    logger.debug(f"{msg} \n{callers_str}", extra={"command_prefix": prefix})


def setup_logging(
    level: Any,
    root_log_name: str = __name__.split(".")[0],
    default_prefix: str = "clan",
) -> None:
    # Get the root logger and set its level
    main_logger = logging.getLogger(root_log_name)
    main_logger.setLevel(level)

    # Create and add the default handler
    default_handler = logging.StreamHandler()

    # Create and add your custom handler
    default_handler.setLevel(level)
    trace_prints = bool(int(os.environ.get("TRACE_PRINT", "0")))
    default_handler.setFormatter(PrefixFormatter(trace_prints, default_prefix))
    main_logger.addHandler(default_handler)
