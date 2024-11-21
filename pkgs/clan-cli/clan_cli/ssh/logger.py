# Adapted from https://github.com/numtide/deploykit

import logging
import os
import sys

# https://no-color.org
DISABLE_COLOR = not sys.stderr.isatty() or os.environ.get("NO_COLOR", "") != ""


def ansi_color(color: int) -> str:
    return f"\x1b[{color}m"


class CommandFormatter(logging.Formatter):
    """
    print errors in red and warnings in yellow
    """

    def __init__(self) -> None:
        super().__init__(
            "%(prefix_color)s[%(command_prefix)s]%(color_reset)s %(color)s%(message)s%(color_reset)s"
        )
        self.hostnames: list[str] = []
        self.hostname_color_offset = 1  # first host shouldn't get aggressive red

    def format(self, record: logging.LogRecord) -> str:
        colorcode = 0
        if record.levelno == logging.ERROR:
            colorcode = 31  # red
        if record.levelno == logging.WARNING:
            colorcode = 33  # yellow

        color, prefix_color, color_reset = "", "", ""
        if not DISABLE_COLOR:
            command_prefix = getattr(record, "command_prefix", "")
            color = ansi_color(colorcode)
            prefix_color = ansi_color(self.hostname_colorcode(command_prefix))
            color_reset = "\x1b[0m"

        record.color = color
        record.prefix_color = prefix_color
        record.color_reset = color_reset

        return super().format(record)

    def hostname_colorcode(self, hostname: str) -> int:
        try:
            index = self.hostnames.index(hostname)
        except ValueError:
            self.hostnames += [hostname]
            index = self.hostnames.index(hostname)
        return 31 + (index + self.hostname_color_offset) % 7


def setup_loggers() -> tuple[logging.Logger, logging.Logger]:
    # If we use the default logger here (logging.error etc) or a logger called
    # "deploykit", then cmdlog messages are also posted on the default logger.
    # To avoid this message duplication, we set up a main and command logger
    # and use a "deploykit" main logger.
    kitlog = logging.getLogger("deploykit.main")
    kitlog.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter())

    kitlog.addHandler(ch)

    # use specific logger for command outputs
    cmdlog = logging.getLogger("deploykit.command")
    cmdlog.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(CommandFormatter())

    cmdlog.addHandler(ch)
    return (kitlog, cmdlog)


# loggers for: general deploykit, command output
kitlog, cmdlog = setup_loggers()

info = kitlog.info
warn = kitlog.warning
error = kitlog.error
