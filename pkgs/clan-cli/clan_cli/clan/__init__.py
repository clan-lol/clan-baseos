# !/usr/bin/env python3
import argparse

from clan_cli.clan.inspect import register_inspect_parser

from .create import register_create_parser
from .list import register_list_parser


# takes a (sub)parser and configures it
def register_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )
    create_parser = subparser.add_parser("create", help="Create a clan")
    register_create_parser(create_parser)
    inspect_parser = subparser.add_parser("inspect", help="Inspect a clan ")
    register_inspect_parser(inspect_parser)
    list_parser = subparser.add_parser("list", help="List clan templates")
    register_list_parser(list_parser)
