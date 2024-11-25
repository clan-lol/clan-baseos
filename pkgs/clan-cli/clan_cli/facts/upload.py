import argparse
import importlib
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine
from clan_cli.ssh.upload import upload

log = logging.getLogger(__name__)


def upload_secrets(machine: Machine) -> None:
    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    secret_facts_store = secret_facts_module.SecretStore(machine=machine)

    if not secret_facts_store.needs_upload():
        log.info("Secrets already uploaded")
        return

    with TemporaryDirectory(prefix="facts-upload-") as tempdir:
        local_secret_dir = Path(tempdir)
        secret_facts_store.upload(local_secret_dir)
        remote_secret_dir = Path(machine.secrets_upload_directory)

        upload(machine.target_host, local_secret_dir, remote_secret_dir)


def upload_command(args: argparse.Namespace) -> None:
    machine = Machine(name=args.machine, flake=args.flake)
    upload_secrets(machine)


def register_upload_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to upload secrets to",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.set_defaults(func=upload_command)
