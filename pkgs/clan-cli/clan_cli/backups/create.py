import argparse
import json
import logging

from clan_cli.completions import (
    add_dynamic_completer,
    complete_backup_providers_for_machine,
    complete_machines,
)
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine

log = logging.getLogger(__name__)


def create_backup(machine: Machine, provider: str | None = None) -> None:
    machine.info(f"creating backup for {machine.name}")
    backup_scripts = json.loads(machine.eval_nix("config.clan.core.backups"))
    if provider is None:
        if not backup_scripts["providers"]:
            msg = "No providers specified"
            raise ClanError(msg)
        for provider in backup_scripts["providers"]:
            proc = machine.target_host.run(
                [backup_scripts["providers"][provider]["create"]],
            )
            if proc.returncode != 0:
                msg = "failed to start backup"
                raise ClanError(msg)
            print("successfully started backup")
    else:
        if provider not in backup_scripts["providers"]:
            msg = f"provider {provider} not found"
            raise ClanError(msg)
        proc = machine.target_host.run(
            [backup_scripts["providers"][provider]["create"]],
        )
        if proc.returncode != 0:
            msg = "failed to start backup"
            raise ClanError(msg)
        print("successfully started backup")


def create_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    machine = Machine(name=args.machine, flake=args.flake)
    create_backup(machine=machine, provider=args.provider)


def register_create_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine", type=str, help="machine in the flake to create backups of"
    )
    add_dynamic_completer(machines_parser, complete_machines)

    provider_action = parser.add_argument(
        "--provider", type=str, help="backup provider to use"
    )
    add_dynamic_completer(provider_action, complete_backup_providers_for_machine)
    parser.set_defaults(func=create_command)
