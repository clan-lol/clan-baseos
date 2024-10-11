# !/usr/bin/env python3
import argparse

from .flash_cmd import register_flash_write_parser
from .list import register_flash_list_parser


# takes a (sub)parser and configures it
def register_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )

    write_parser = subparser.add_parser(
        "write",
        help="Flash a machine to a disk",
    )
    register_flash_write_parser(write_parser)

    list_parser = subparser.add_parser(
        "list", help="List possible keymaps or languages"
    )
    register_flash_list_parser(list_parser)
