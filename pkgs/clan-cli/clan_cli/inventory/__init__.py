"""
All read/write operations MUST use the inventory.

Machine data, clan data or service data can be accessed in a performant way.

This file exports stable classnames for static & dynamic type safety.

Utilize:

- load_inventory_eval: To load the actual inventory with nix declarations merged.
Operate on the returned inventory to make changes
- save_inventory: To persist changes.
"""

import contextlib
import json
from pathlib import Path

from clan_cli.api import API, dataclass_to_dict, from_dict
from clan_cli.cmd import run_no_stdout
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.git import commit_file
from clan_cli.nix import nix_eval

from .classes import (
    AdminConfig,
    Inventory,
    # Machine classes
    Machine,
    MachineDeploy,
    # General classes
    Meta,
    Service,
    # Admin service
    ServiceAdmin,
    ServiceAdminRole,
    ServiceAdminRoleDefault,
    # Borgbackup service
    ServiceBorgbackup,
    ServiceBorgbackupRole,
    ServiceBorgbackupRoleClient,
    ServiceBorgbackupRoleServer,
    ServiceMeta,
    # Single Disk service
    ServiceSingleDisk,
    ServiceSingleDiskRole,
    ServiceSingleDiskRoleDefault,
    SingleDiskConfig,
)

# Re export classes here
# This allows to rename classes in the generated code
__all__ = [
    "from_dict",
    "dataclass_to_dict",
    "Service",
    "Machine",
    "Meta",
    "Inventory",
    "MachineDeploy",
    "ServiceBorgbackup",
    "ServiceMeta",
    "ServiceBorgbackupRole",
    "ServiceBorgbackupRoleClient",
    "ServiceBorgbackupRoleServer",
    # Single Disk service
    "ServiceSingleDisk",
    "ServiceSingleDiskRole",
    "ServiceSingleDiskRoleDefault",
    "SingleDiskConfig",
    # Admin service
    "ServiceAdmin",
    "ServiceAdminRole",
    "ServiceAdminRoleDefault",
    "AdminConfig",
]


def get_path(flake_dir: str | Path) -> Path:
    """
    Get the path to the inventory file in the flake directory
    """
    return (Path(flake_dir) / "inventory.json").resolve()


# Default inventory
default_inventory = Inventory(
    meta=Meta(name="New Clan"), machines={}, services=Service()
)


def load_inventory_eval(flake_dir: str | Path) -> Inventory:
    """
    Loads the actual inventory.
    After all merge operations with eventual nix code in buildClan.

    Evaluates clanInternals.inventory with nix. Which is performant.

    - Contains all clan metadata
    - Contains all machines
    - and more
    """
    cmd = nix_eval(
        [
            f"{flake_dir}#clanInternals.inventory",
            "--json",
        ]
    )

    proc = run_no_stdout(cmd)

    try:
        res = proc.stdout.strip()
        data = json.loads(res)
        inventory = from_dict(Inventory, data)
        return inventory
    except json.JSONDecodeError as e:
        msg = f"Error decoding inventory from flake: {e}"
        raise ClanError(msg) from e


def load_inventory_json(
    flake_dir: str | Path, default: Inventory = default_inventory
) -> Inventory:
    """
    Load the inventory file from the flake directory
    If not file is found, returns the default inventory
    """
    inventory = default

    inventory_file = get_path(flake_dir)
    if inventory_file.exists():
        with open(inventory_file) as f:
            try:
                res = json.load(f)
                inventory = from_dict(Inventory, res)
            except json.JSONDecodeError as e:
                # Error decoding the inventory file
                msg = f"Error decoding inventory file: {e}"
                raise ClanError(msg) from e

    if not inventory_file.exists():
        # Copy over the meta from the flake if the inventory is not initialized
        inventory.meta = load_inventory_eval(flake_dir).meta

    return inventory


def save_inventory(inventory: Inventory, flake_dir: str | Path, message: str) -> None:
    """ "
    Write the inventory to the flake directory
    and commit it to git with the given message
    """
    inventory_file = get_path(flake_dir)

    with open(inventory_file, "w") as f:
        json.dump(dataclass_to_dict(inventory), f, indent=2)

    commit_file(inventory_file, Path(flake_dir), commit_message=message)


@API.register
def init_inventory(directory: str, init: Inventory | None = None) -> None:
    inventory = None
    # Try reading the current flake
    if init is None:
        with contextlib.suppress(ClanCmdError):
            inventory = load_inventory_eval(directory)

    if init is not None:
        inventory = init

    # Write inventory.json file
    if inventory is not None:
        # Persist creates a commit message for each change
        save_inventory(inventory, directory, "Init inventory")
