# !/usr/bin/env python3
import argparse

from .flash_command import register_flash_apply_parser
from .list import register_flash_list_parser


# takes a (sub)parser and configures it
def register_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )

    apply_parser = subparser.add_parser(
        "apply",
        help="Flash a machine",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_flash_apply_parser(apply_parser)

    list_parser = subparser.add_parser(
        "list",
        help="List options",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_flash_list_parser(list_parser)
