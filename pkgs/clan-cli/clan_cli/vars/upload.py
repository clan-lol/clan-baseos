import argparse
import importlib
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

log = logging.getLogger(__name__)


def upload_secret_vars(machine: Machine) -> None:
    secret_store_module = importlib.import_module(machine.secret_vars_module)
    secret_store = secret_store_module.SecretStore(machine=machine)

    if not secret_store.needs_upload():
        log.info("Secrets already uploaded")
        return
    with TemporaryDirectory(prefix="vars-upload-") as tempdir:
        secret_dir = Path(tempdir)
        secret_store.upload(secret_dir)
        machine.target_host.upload(
            secret_dir, Path(machine.secret_vars_upload_directory)
        )


def upload_command(args: argparse.Namespace) -> None:
    machine = Machine(name=args.machine, flake=args.flake)
    upload_secret_vars(machine)


def register_upload_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to upload secrets to",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.set_defaults(func=upload_command)
