import argparse
import logging
import shutil

from clan_cli.api import API
from clan_cli.clan_uri import Flake
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.dirs import specific_machine_dir
from clan_cli.errors import ClanError
from clan_cli.inventory import get_inventory, set_inventory

log = logging.getLogger(__name__)


@API.register
def delete_machine(flake: Flake, name: str) -> None:
    inventory = get_inventory(flake.path)

    if "machines" not in inventory:
        msg = "No machines in inventory"
        raise ClanError(msg)

    machine = inventory["machines"].pop(name, None)
    if machine is None:
        msg = f"Machine {name} does not exist"
        raise ClanError(msg)

    set_inventory(inventory, flake.path, f"Delete machine {name}")

    folder = specific_machine_dir(flake.path, name)
    if folder.exists():
        shutil.rmtree(folder)


def delete_command(args: argparse.Namespace) -> None:
    delete_machine(args.flake, args.name)


def register_delete_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument("name", type=str)
    add_dynamic_completer(machines_parser, complete_machines)

    parser.set_defaults(func=delete_command)
