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


def flatten_data(data: dict, parent_key: str = "", separator: str = ".") -> dict:
    """
    Recursively flattens a nested dictionary structure where keys are joined by the separator.
    The flattened dictionary contains only entries with "__prio".

    Args:
        data (dict): The nested dictionary structure.
        parent_key (str): The current path to the nested dictionary (used for recursion).
        separator (str): The string to use for joining keys.

    Returns:
        dict: A flattened dictionary with "__prio" values.
    """
    flattened = {}

    for key, value in data.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key

        if isinstance(value, dict) and "__prio" in value:
            flattened[new_key] = {"__prio": value["__prio"]}

        if isinstance(value, dict):
            # Recursively flatten the nested dictionary
            flattened.update(flatten_data(value, new_key, separator))

    return flattened


def determine_writeability(
    data: dict,
    correlated: dict,
    parent_key: str = "",
    parent_prio: int | None = None,
    results: dict | None = None,
    non_writeable: bool = False,
) -> dict:
    if results is None:
        results = {"writeable": set({}), "non_writeable": set({})}

    for key, value in data.items():
        if key == "__prio":
            continue

        full_key = f"{parent_key}.{key}" if parent_key else key

        # Determine the priority for the current key
        # Inherit from parent if no priority is defined
        prio = value.get("__prio", None)
        if prio is None:
            prio = parent_prio

        # If priority is less than 100, all children are not writeable
        # If the parent passed "non_writeable" earlier, this makes all children not writeable
        if (prio is not None and prio < 100) or non_writeable:
            results["non_writeable"].add(full_key)
            if isinstance(value, dict):
                determine_writeability(
                    value,
                    {},  # Children won't be writeable, so correlation doesn't matter here
                    full_key,
                    prio,  # Pass the same priority down
                    results,
                    # Recursively mark all children as non-writeable
                    non_writeable=True,
                )
            continue

        # Check if the key is writeable otherwise
        key_in_correlated = key in correlated
        if prio is None:
            msg = f"Priority for key '{full_key}' is not defined. Cannot determine if it is writeable."
            raise ClanError(msg)

        has_children = any(k != "__prio" for k in value)
        is_writeable = prio > 100 or key_in_correlated or has_children

        # Append the result
        if is_writeable:
            results["writeable"].add(full_key)
        else:
            results["non_writeable"].add(full_key)

        # Recursive
        if isinstance(value, dict):
            determine_writeability(
                value,
                correlated.get(key, {}),
                full_key,
                prio,  # Pass down current priority
                results,
            )

    return results


def get_inventory_current_priority(flake_dir: str | Path) -> dict:
    """
    Returns the current priority of the inventory values

    machines = {
        __prio = 100;
        flash-installer = {
            __prio = 100;
            deploy = {
                targetHost = { __prio = 1500; };
            };
            description = { __prio = 1500; };
            icon = { __prio = 1500; };
            name = { __prio = 1500; };
            tags = { __prio = 1500; };
        };
    }
    """
    cmd = nix_eval(
        [
            f"{flake_dir}#clanInternals.inventoryValuesPrios",
            "--json",
        ]
    )

    proc = run_no_stdout(cmd)

    try:
        res = proc.stdout.strip()
        data = json.loads(res)
    except json.JSONDecodeError as e:
        msg = f"Error decoding inventory from flake: {e}"
        raise ClanError(msg) from e
    else:
        return data


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


def patch(d: dict[str, Any], path: str, content: Any) -> None:
    """
    Update the value at a specific dot-separated path in a nested dictionary.

    If the value didn't exist before, it will be created recursively.

    :param d: The dictionary to update.
    :param path: The dot-separated path to the key (e.g., 'foo.bar').
    :param content: The new value to set.
    """
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = content


@API.register
def patch_inventory_with(base_dir: Path, section: str, content: dict[str, Any]) -> None:
    inventory_file = get_path(base_dir)

    curr_inventory = {}
    with inventory_file.open("r") as f:
        curr_inventory = json.load(f)

    patch(curr_inventory, section, content)

    with inventory_file.open("w") as f:
        json.dump(curr_inventory, f, indent=2)

    commit_file(inventory_file, base_dir, commit_message=f"inventory.{section}: Update")


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
