import argparse
import logging
import re

from clan_cli.api import API
from clan_cli.clan_uri import FlakeId
from clan_cli.errors import ClanError
from clan_cli.inventory import (
    Machine,
    MachineDeploy,
    load_inventory_eval,
    load_inventory_json,
    set_inventory,
)

log = logging.getLogger(__name__)


@API.register
def create_machine(flake: FlakeId, machine: Machine) -> None:
    hostname_regex = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    if not re.match(hostname_regex, machine.name):
        msg = "Machine name must be a valid hostname"
        raise ClanError(msg, location="Create Machine")

    inventory = load_inventory_json(flake.path)

    full_inventory = load_inventory_eval(flake.path)

    if machine.name in full_inventory.machines:
        msg = f"Machine with the name {machine.name} already exists"
        raise ClanError(msg)

    print(f"Define machine {machine.name}", machine)

    inventory.machines.update({machine.name: machine})
    set_inventory(inventory, flake.path, f"Create machine {machine.name}")


def create_command(args: argparse.Namespace) -> None:
    create_machine(
        args.flake,
        Machine(
            name=args.machine,
            system=args.system,
            description=args.description,
            tags=args.tags,
            icon=args.icon,
            deploy=MachineDeploy(),
        ),
    )


def register_create_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("machine", type=str)
    parser.set_defaults(func=create_command)

    parser.add_argument(
        "--system",
        type=str,
        default=None,
        help="Host platform to use. i.e. 'x86_64-linux' or 'aarch64-darwin' etc.",
        metavar="PLATFORM",
    )
    parser.add_argument(
        "--description",
        type=str,
        default=None,
        help="A description of the machine.",
    )
    parser.add_argument(
        "--icon",
        type=str,
        default=None,
        help="Path to an icon to use for the machine. - Must be a path to icon file relative to the flake directory, or a public url.",
        metavar="PATH",
    )
    parser.add_argument(
        "--tags",
        nargs="+",
        default=[],
        help="Tags to associate with the machine. Can be used to assign multiple machines to services.",
    )
