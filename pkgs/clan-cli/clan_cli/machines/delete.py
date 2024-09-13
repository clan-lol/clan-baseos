import argparse
import shutil

from clan_cli.api import API
from clan_cli.clan_uri import FlakeId
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.dirs import specific_machine_dir
from clan_cli.errors import ClanError
from clan_cli.inventory import load_inventory_json, set_inventory


@API.register
def delete_machine(flake: FlakeId, name: str) -> None:
    inventory = load_inventory_json(flake.path)

    machine = inventory.machines.pop(name, None)
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
