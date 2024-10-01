import argparse
import importlib
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import Log, run
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

log = logging.getLogger(__name__)


def upload_secrets(machine: Machine) -> None:
    secret_store_module = importlib.import_module(machine.secret_facts_module)
    secret_store = secret_store_module.SecretStore(machine=machine)

    if secret_store.update_check():
        log.info("Secrets already up to date")
        return
    with TemporaryDirectory(prefix="vars-upload-") as tempdir:
        secret_store.upload(Path(tempdir))
        host = machine.target_host

        ssh_cmd = host.ssh_cmd()
        run(
            nix_shell(
                ["nixpkgs#rsync"],
                [
                    "rsync",
                    "-e",
                    " ".join(["ssh"] + ssh_cmd[2:]),
                    "--recursive",
                    "--links",
                    "--times",
                    "--compress",
                    "--delete",
                    "--chmod=D700,F600",
                    f"{tempdir!s}/",
                    f"{host.user}@{host.host}:{machine.secrets_upload_directory}/",
                ],
            ),
            log=Log.BOTH,
        )


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
