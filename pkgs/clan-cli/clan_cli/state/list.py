import argparse
import json
import logging
from pathlib import Path

from clan_cli.cmd import run_no_stdout
from clan_cli.completions import (
    add_dynamic_completer,
    complete_machines,
    complete_state_services_for_machine,
)
from clan_cli.dirs import get_clan_flake_toplevel_or_env
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.nix import nix_eval

log = logging.getLogger(__name__)


def list_state_folders(machine: str, service: None | str = None) -> None:
    uri = "TODO"
    if (clan_dir_result := get_clan_flake_toplevel_or_env()) is not None:
        flake = clan_dir_result
    else:
        flake = Path()
    cmd = nix_eval(
        [
            f"{flake}#nixosConfigurations.{machine}.config.clan.core.state",
            "--json",
        ]
    )
    res = "{}"

    try:
        proc = run_no_stdout(cmd)
        res = proc.stdout.strip()
    except ClanCmdError as e:
        msg = "Clan might not have meta attributes"
        raise ClanError(
            msg,
            location=f"show_clan {uri}",
            description="Evaluation failed on clanInternals.meta attribute",
        ) from e

    state = json.loads(res)
    if service:
        if state_info := state.get(service):
            state = {service: state_info}
        else:
            msg = f"Service {service} isn't configured for this machine."
            raise ClanError(
                msg,
                location=f"clan state list {machine} --service {service}",
                description=f"The service: {service} needs to be configured for the machine.",
            )

    for service in state:
        print(f"· service: {service}")
        if folders := state.get(service)["folders"]:
            print("  folders:")
            for folder in folders:
                print(f"  - {folder}")
        if pre_backup := state.get(service)["preBackupCommand"]:
            print(f"  preBackupCommand: {pre_backup}")
        if pre_restore := state.get(service)["preRestoreCommand"]:
            print(f"  preRestoreCommand: {pre_restore}")
        if post_restore := state.get(service)["postRestoreCommand"]:
            print(f"  postRestoreCommand: {post_restore}")
        print("")


def list_command(args: argparse.Namespace) -> None:
    list_state_folders(machine=args.machine, service=args.service)


def register_state_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to list state files for",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    service_parser = parser.add_argument(
        "--service",
        help="the service to show state files for",
    )
    add_dynamic_completer(service_parser, complete_state_services_for_machine)
    parser.set_defaults(func=list_command)
