import argparse
import json
import subprocess

from clan_cli.completions import (
    add_dynamic_completer,
    complete_backup_providers_for_machine,
    complete_machines,
)
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine


def restore_service(machine: Machine, name: str, provider: str, service: str) -> None:
    backup_metadata = json.loads(machine.eval_nix("config.clan.core.backups"))
    backup_folders = json.loads(machine.eval_nix("config.clan.core.state"))

    if service not in backup_folders:
        msg = f"Service {service} not found in configuration. Available services are: {', '.join(backup_folders.keys())}"
        raise ClanError(msg)

    folders = backup_folders[service]["folders"]
    env = {}
    env["NAME"] = name
    # FIXME: If we have too many folder this might overflow the stack.
    env["FOLDERS"] = ":".join(set(folders))

    if pre_restore := backup_folders[service]["preRestoreCommand"]:
        proc = machine.target_host.run(
            [pre_restore],
            stdout=subprocess.PIPE,
            extra_env=env,
        )
        if proc.returncode != 0:
            raise ClanError(
                f"failed to run preRestoreCommand: {pre_restore}, error was: {proc.stdout}"
            )

    proc = machine.target_host.run(
        [backup_metadata["providers"][provider]["restore"]],
        stdout=subprocess.PIPE,
        extra_env=env,
    )
    if proc.returncode != 0:
        raise ClanError(
            f"failed to restore backup: {backup_metadata['providers'][provider]['restore']}"
        )

    if post_restore := backup_folders[service]["postRestoreCommand"]:
        proc = machine.target_host.run(
            [post_restore],
            stdout=subprocess.PIPE,
            extra_env=env,
        )
        if proc.returncode != 0:
            raise ClanError(
                f"failed to run postRestoreCommand: {post_restore}, error was: {proc.stdout}"
            )


def restore_backup(
    machine: Machine,
    provider: str,
    name: str,
    service: str | None = None,
) -> None:
    errors = []
    if service is None:
        backup_folders = json.loads(machine.eval_nix("config.clan.core.state"))
        for _service in backup_folders:
            try:
                restore_service(machine, name, provider, _service)
            except ClanError as e:
                errors.append(f"{_service}: {e}")
    else:
        try:
            restore_service(machine, name, provider, service)
        except ClanError as e:
            errors.append(f"{service}: {e}")
    if errors:
        raise ClanError(
            "Restore failed for the following services:\n" + "\n".join(errors)
        )


def restore_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        raise ClanError("Could not find clan flake toplevel directory")
    machine = Machine(name=args.machine, flake=args.flake)
    restore_backup(
        machine=machine,
        provider=args.provider,
        name=args.name,
        service=args.service,
    )


def register_restore_parser(parser: argparse.ArgumentParser) -> None:
    machine_action = parser.add_argument(
        "machine", type=str, help="machine in the flake to create backups of"
    )
    add_dynamic_completer(machine_action, complete_machines)
    provider_action = parser.add_argument(
        "provider", type=str, help="backup provider to use"
    )
    add_dynamic_completer(provider_action, complete_backup_providers_for_machine)
    parser.add_argument("name", type=str, help="Name of the backup to restore")
    parser.add_argument("--service", type=str, help="name of the service to restore")
    parser.set_defaults(func=restore_command)
