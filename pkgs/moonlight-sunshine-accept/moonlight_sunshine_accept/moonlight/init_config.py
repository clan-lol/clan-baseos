import argparse
from pathlib import Path

from .state import init_state


def init_config(args: argparse.Namespace) -> None:
    init_state(args.certificate.read_text(), args.key.read_text())
    print("Finished initializing moonlight state.")


def register_config_initialization_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--certificate", type=Path)
    parser.add_argument("--key", type=Path)
    parser.set_defaults(func=init_config)
