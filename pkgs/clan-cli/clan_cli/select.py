import argparse
import json

from clan_cli.flake import Flake


def select_command(args: argparse.Namespace) -> None:
    flake = Flake(args.flake.path)
    print(json.dumps(flake.select(args.selector), indent=4))


def register_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=select_command)
    parser.add_argument(
        "selector",
        help="select from a flake",
    )
    parser.add_argument(
        "--impure",
        action="store_true",
        default=False,
    )
