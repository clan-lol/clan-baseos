import argparse
import importlib
import logging
from pathlib import Path

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

log = logging.getLogger(__name__)


def upload_secret_vars(machine: Machine, directory: Path | None = None) -> None:
    secret_store_module = importlib.import_module(machine.secret_vars_module)
    secret_store = secret_store_module.SecretStore(machine=machine)
    if directory:
        secret_store.populate_dir(directory, phases=["activation", "users", "services"])
    else:
        secret_store.upload(phases=["activation", "users", "services"])


def upload_command(args: argparse.Namespace) -> None:
    machine = Machine(name=args.machine, flake=args.flake)
    directory = None
    if args.directory:
        directory = Path(args.directory)
    upload_secret_vars(machine, directory)


def register_upload_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to upload secrets to",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.add_argument(
        "--directory",
        help="If provided, secrets will be copied into this directory instead of the remote server",
    )
    parser.set_defaults(func=upload_command)
