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
from collections import Counter
from dataclasses import dataclass
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


def get_inventory_path(flake_dir: str | Path) -> Path:
    """
    Get the path to the inventory file in the flake directory
    """
    inventory_file = (Path(flake_dir) / "inventory.json").resolve()
    return inventory_file


# Default inventory
default_inventory: Inventory = {"meta": {"name": "New Clan"}}


@API.register
def load_inventory_eval(flake_dir: str | Path) -> Inventory:
    """
    Loads the evaluated inventory.
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
        data: dict = json.loads(res)
        inventory = Inventory(data)  # type: ignore
    except json.JSONDecodeError as e:
        msg = f"Error decoding inventory from flake: {e}"
        raise ClanError(msg) from e
    else:
        return inventory


def flatten_data(data: dict, parent_key: str = "", separator: str = ".") -> dict:
    """
    Recursively flattens a nested dictionary structure where keys are joined by the separator.

    Args:
        data (dict): The nested dictionary structure.
        parent_key (str): The current path to the nested dictionary (used for recursion).
        separator (str): The string to use for joining keys.

    Returns:
        dict: A flattened dictionary with all values. Directly in the root.
    """
    flattened = {}

    for key, value in data.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key

        if isinstance(value, dict):
            # Recursively flatten the nested dictionary
            flattened.update(flatten_data(value, new_key, separator))
        else:
            flattened[new_key] = value

    return flattened


def unmerge_lists(all_items: list, filter_items: list) -> list:
    """
    Unmerge the current list. Given a previous list.

    Returns:
        The other list.
    """
    # Unmerge the lists
    res = []
    for value in all_items:
        if value not in filter_items:
            res.append(value)

    return res


def find_duplicates(string_list: list[str]) -> list[str]:
    count = Counter(string_list)
    duplicates = [item for item, freq in count.items() if freq > 1]
    return duplicates


def find_deleted_paths(
    persisted: dict[str, Any], update: dict[str, Any], parent_key: str = ""
) -> set[str]:
    """
    Recursively find keys (at any nesting level) that exist in persisted but do not
    exist in update. If a nested dictionary is completely removed, return that dictionary key.

    :param persisted: The original (persisted) nested dictionary.
    :param update: The updated nested dictionary (some keys might be removed).
    :param parent_key: The dotted path to the current dictionary's location.
    :return: A set of dotted paths indicating keys or entire nested paths that were deleted.
    """
    deleted_paths = set()

    # Iterate over keys in persisted
    for key, p_value in persisted.items():
        current_path = f"{parent_key}.{key}" if parent_key else key
        # Check if this key exists in update
        if key not in update:
            # Key doesn't exist at all -> entire branch deleted
            deleted_paths.add(current_path)
        else:
            u_value = update[key]
            # If persisted value is dict, check the update value
            if isinstance(p_value, dict):
                if isinstance(u_value, dict):
                    # If persisted dict is non-empty but updated dict is empty,
                    # that means everything under this branch is removed.
                    if p_value and not u_value:
                        # All children are removed
                        for child_key in p_value:
                            child_path = f"{current_path}.{child_key}"
                            deleted_paths.add(child_path)
                    else:
                        # Both are dicts, recurse deeper
                        deleted_paths |= find_deleted_paths(
                            p_value, u_value, current_path
                        )
                else:
                    # Persisted was a dict, update is not a dict -> entire branch changed
                    # Consider this as a full deletion of the persisted branch
                    deleted_paths.add(current_path)

    return deleted_paths


def calc_patches(
    persisted: dict[str, Any],
    update: dict[str, Any],
    all_values: dict[str, Any],
    writeables: dict[str, set[str]],
) -> tuple[dict[str, Any], set[str]]:
    """
    Calculate the patches to apply to the inventory.

    Given its current state and the update to apply.

    Filters out nix-values so it doesnt matter if the anyone sends them.

    : param persisted: The current state of the inventory.
    : param update: The update to apply.
    : param writeable: The writeable keys. Use 'determine_writeability'.
        Example: {'writeable': {'foo', 'foo.bar'}, 'non_writeable': {'foo.nix'}}
    : param all_values: All values in the inventory retrieved from the flake evaluation.

    Returns a tuple with the SET and DELETE patches.
    """
    persisted_flat = flatten_data(persisted)
    update_flat = flatten_data(update)
    all_values_flat = flatten_data(all_values)

    def is_writeable_key(key: str) -> bool:
        """
        Recursively check if a key is writeable.
        key "machines.machine1.deploy.targetHost" is specified but writeability is only defined for "machines"
        We pop the last key and check if the parent key is writeable/non-writeable.
        """
        remaining = key.split(".")
        while remaining:
            if ".".join(remaining) in writeables["writeable"]:
                return True
            if ".".join(remaining) in writeables["non_writeable"]:
                return False

            remaining.pop()

        msg = f"Cannot determine writeability for key '{key}'"
        raise ClanError(msg, description="F001")

    patchset = {}
    for update_key, update_data in update_flat.items():
        if not is_writeable_key(update_key):
            if update_data != all_values_flat.get(update_key):
                msg = f"Key '{update_key}' is not writeable."
                raise ClanError(msg)
            continue

        if is_writeable_key(update_key):
            prev_value = all_values_flat.get(update_key)
            if prev_value and type(update_data) is not type(prev_value):
                msg = f"Type mismatch for key '{update_key}'. Cannot update {type(all_values_flat.get(update_key))} with {type(update_data)}"
                raise ClanError(msg)

            # Handle list separation
            if isinstance(update_data, list):
                duplicates = find_duplicates(update_data)
                if duplicates:
                    msg = f"Key '{update_key}' contains duplicates: {duplicates}. This not supported yet."
                    raise ClanError(msg)
                # List of current values
                persisted_data = persisted_flat.get(update_key, [])
                # List including nix values
                all_list = all_values_flat.get(update_key, [])
                nix_list = unmerge_lists(all_list, persisted_data)
                if update_data != all_list:
                    patchset[update_key] = unmerge_lists(update_data, nix_list)

            elif update_data != persisted_flat.get(update_key, None):
                patchset[update_key] = update_data

            continue

        msg = f"Cannot determine writeability for key '{update_key}'"
        raise ClanError(msg)

    delete_set = find_deleted_paths(persisted, update)

    for delete_key in delete_set:
        if not is_writeable_key(delete_key):
            msg = f"Cannot delete: Key '{delete_key}' is not writeable."
            raise ClanError(msg)

    return patchset, delete_set


def determine_writeability(
    priorities: dict[str, Any],
    defaults: dict[str, Any],
    persisted: dict[str, Any],
    parent_key: str = "",
    parent_prio: int | None = None,
    results: dict | None = None,
    non_writeable: bool = False,
) -> dict[str, set[str]]:
    if results is None:
        results = {"writeable": set({}), "non_writeable": set({})}

    for key, value in priorities.items():
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
                    defaults,
                    {},  # Children won't be writeable, so correlation doesn't matter here
                    full_key,
                    prio,  # Pass the same priority down
                    results,
                    # Recursively mark all children as non-writeable
                    non_writeable=True,
                )
            continue

        # Check if the key is writeable otherwise
        key_in_correlated = key in persisted
        if prio is None:
            msg = f"Priority for key '{full_key}' is not defined. Cannot determine if it is writeable."
            raise ClanError(msg)

        is_mergeable = False
        if prio == 100:
            default = defaults.get(key)
            if isinstance(default, dict):
                is_mergeable = True
            if isinstance(default, list):
                is_mergeable = True
            if key_in_correlated:
                is_mergeable = True

        is_writeable = prio > 100 or is_mergeable

        # Append the result
        if is_writeable:
            results["writeable"].add(full_key)
        else:
            results["non_writeable"].add(full_key)

        # Recursive
        if isinstance(value, dict):
            determine_writeability(
                value,
                defaults.get(key, {}),
                persisted.get(key, {}),
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
def load_inventory_json(flake_dir: str | Path) -> Inventory:
    """
    Load the inventory FILE from the flake directory
    If no file is found, returns an empty dictionary

    DO NOT USE THIS FUNCTION TO READ THE INVENTORY

    Use load_inventory_eval instead
    """

    inventory_file = get_inventory_path(flake_dir)

    if not inventory_file.exists():
        return {}
    with inventory_file.open() as f:
        try:
            res: dict = json.load(f)
            inventory = Inventory(res)  # type: ignore
        except json.JSONDecodeError as e:
            # Error decoding the inventory file
            msg = f"Error decoding inventory file: {e}"
            raise ClanError(msg) from e

    return inventory


def delete_by_path(d: dict[str, Any], path: str) -> Any:
    """
    Deletes the nested entry specified by a dot-separated path from the dictionary using pop().

    :param data: The dictionary to modify.
    :param path: A dot-separated string indicating the nested key to delete.
                 e.g., "foo.bar.baz" will attempt to delete data["foo"]["bar"]["baz"].

    :raises KeyError: If any intermediate key is missing or not a dictionary,
                      or if the final key to delete is not found.
    """
    if not path:
        msg = "Cannot delete. Path is empty."
        raise ClanError(msg)

    keys = path.split(".")
    current = d

    # Navigate to the parent dictionary of the final key
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            msg = f"Cannot delete. Key '{path}' not found or not a dictionary '{d}'."
            raise ClanError(msg)
        current = current[key]

    # Attempt to pop the final key
    last_key = keys[-1]
    try:
        value = current.pop(last_key)
    except KeyError:
        msg = f"Cannot delete. Path '{path}' not found in data '{d}'. "
        raise ClanError(msg) from KeyError
    else:
        return {last_key: value}


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
    """
    Pass only the section to update and the content to update with.
    Make sure you pass only attributes that you would like to persist.
    ATTENTION: Don't pass nix eval values unintentionally.
    """

    inventory_file = get_inventory_path(base_dir)

    curr_inventory = {}
    if inventory_file.exists():
        with inventory_file.open("r") as f:
            curr_inventory = json.load(f)

    patch(curr_inventory, section, content)

    with inventory_file.open("w") as f:
        json.dump(curr_inventory, f, indent=2)

    commit_file(inventory_file, base_dir, commit_message=f"inventory.{section}: Update")


@dataclass
class WriteInfo:
    writeables: dict[str, set[str]]
    data_eval: Inventory
    data_disk: Inventory


@API.register
def get_inventory_with_writeable_keys(
    flake_dir: str | Path,
) -> WriteInfo:
    """
    Load the inventory and determine the writeable keys
    Performs 2 nix evaluations to get the current priority and the inventory
    """
    current_priority = get_inventory_current_priority(flake_dir)

    data_eval: Inventory = load_inventory_eval(flake_dir)
    data_disk: Inventory = load_inventory_json(flake_dir)

    writeables = determine_writeability(
        current_priority, dict(data_eval), dict(data_disk)
    )

    return WriteInfo(writeables, data_eval, data_disk)


@API.register
def set_inventory(
    inventory: Inventory, flake_dir: str | Path, message: str, commit: bool = True
) -> None:
    """
    Write the inventory to the flake directory
    and commit it to git with the given message
    """

    write_info = get_inventory_with_writeable_keys(flake_dir)

    # Remove internals from the inventory
    inventory.pop("tags", None)  # type: ignore
    inventory.pop("options", None)  # type: ignore
    inventory.pop("assertions", None)  # type: ignore

    patchset, delete_set = calc_patches(
        dict(write_info.data_disk),
        dict(inventory),
        dict(write_info.data_eval),
        write_info.writeables,
    )
    persisted = dict(write_info.data_disk)

    for patch_path, data in patchset.items():
        patch(persisted, patch_path, data)

    for delete_path in delete_set:
        delete_by_path(persisted, delete_path)

    inventory_file = get_inventory_path(flake_dir)
    with inventory_file.open("w") as f:
        json.dump(persisted, f, indent=2)

    if commit:
        commit_file(inventory_file, Path(flake_dir), commit_message=message)


@API.register
def delete(directory: str | Path, delete_set: set[str]) -> None:
    """
    Delete keys from the inventory
    """
    write_info = get_inventory_with_writeable_keys(directory)

    data_disk = dict(write_info.data_disk)

    for delete_path in delete_set:
        delete_by_path(data_disk, delete_path)

    inventory_file = get_inventory_path(directory)
    with inventory_file.open("w") as f:
        json.dump(data_disk, f, indent=2)

    commit_file(
        inventory_file,
        Path(directory),
        commit_message=f"Delete inventory keys {delete_set}",
    )


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
def get_inventory(base_path: str | Path) -> Inventory:
    return load_inventory_eval(base_path)
