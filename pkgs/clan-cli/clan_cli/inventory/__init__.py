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
from typing import Any

from clan_cli.api import API, dataclass_to_dict, from_dict
from clan_cli.cmd import run_no_stdout
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.git import commit_file
from clan_cli.nix import nix_eval

from .classes import (
    Inventory,
    # Machine classes
    Machine,
    MachineDeploy,
    # General classes
    Meta,
    Service,
)

# Re export classes here
# This allows to renaming of classes in the generated code
__all__ = [
    "Inventory",
    "Machine",
    "MachineDeploy",
    "Meta",
    "Service",
    "dataclass_to_dict",
    "from_dict",
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


@API.register
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
    except json.JSONDecodeError as e:
        msg = f"Error decoding inventory from flake: {e}"
        raise ClanError(msg) from e
    else:
        return inventory


@API.register
def load_inventory_json(
    flake_dir: str | Path, default: Inventory = default_inventory
) -> Inventory:
    """
    Load the inventory file from the flake directory
    If no file is found, returns the default inventory
    """
    inventory = default

    inventory_file = get_path(flake_dir)
    if inventory_file.exists():
        with inventory_file.open() as f:
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


@API.register
def set_inventory(
    inventory: Inventory | dict[str, Any], flake_dir: str | Path, message: str
) -> None:
    """ "
    Write the inventory to the flake directory
    and commit it to git with the given message
    """
    inventory_file = get_path(flake_dir)

    # Filter out modules not set via UI.
    # It is not possible to set modules from "/nix/store" via the UI
    modules = {}
    filtered_modules = lambda m: {
        key: value for key, value in m.items() if "/nix/store" not in value
    }
    if isinstance(inventory, dict):
        modules = filtered_modules(inventory.get("modules", {}))  # type: ignore
        inventory["modules"] = modules
    else:
        modules = filtered_modules(inventory.modules)  # type: ignore
        inventory.modules = modules

    with inventory_file.open("w") as f:
        if isinstance(inventory, Inventory):
            json.dump(dataclass_to_dict(inventory), f, indent=2)
        else:
            json.dump(inventory, f, indent=2)

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
        set_inventory(inventory, directory, "Init inventory")


@API.register
def merge_template_inventory(
    inventory: Inventory, template_inventory: Inventory, machine_name: str
) -> None:
    """
    Merge the template inventory into the current inventory
    The template inventory is expected to be a subset of the current inventory
    """
    for service_name, instance in template_inventory.services.items():
        if len(instance.keys()) > 0:
            msg = f"Service {service_name} in template inventory has multiple instances"
            description = (
                "Only one instance per service is allowed in a template inventory"
            )
            raise ClanError(msg, description=description)

        # services.<service_name>.<instance_name>.config
        config = next((v for v in instance.values() if "config" in v), None)
        if not config:
            msg = f"Service {service_name} in template inventory has no config"
            description = "Invalid inventory configuration"
            raise ClanError(msg, description=description)

        # Disallow "config.machines" key
        if "machines" in config:
            msg = f"Service {service_name} in template inventory has machines"
            description = "The 'machines' key is not allowed in template inventory"
            raise ClanError(msg, description=description)

        # Require "config.roles" key
        if "roles" not in config:
            msg = f"Service {service_name} in template inventory has no roles"
            description = "roles key is required in template inventory"
            raise ClanError(msg, description=description)

        # TODO: Implement merging of template inventory
        msg = "Merge template inventory is not implemented yet"
        raise NotImplementedError(msg)
