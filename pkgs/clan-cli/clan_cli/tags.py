import json
from pathlib import Path
from typing import Any

from clan_cli.cmd import run_no_stdout
from clan_cli.errors import ClanError
from clan_cli.nix import nix_eval


def list_tagged_machines(flake_url: str | Path) -> dict[str, Any]:
    """
    Query machines from the inventory with their meta information intact.
    The meta information includes tags.
    """
    cmd = nix_eval(
        [
            f"{flake_url}#clanInternals.inventory.machines",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)

    try:
        res = proc.stdout.strip()
        data = json.loads(res)
    except json.JSONDecodeError as e:
        msg = f"Error decoding tagged inventory machines from flake: {e}"
        raise ClanError(msg) from e
    else:
        return data


def query_machines_by_tags(
    flake_path: str | Path, tags: list[str] | None = None
) -> list[str]:
    """
    Query machines by their respective tags, if multiple tags are specified
    then only machines that have those respective tags specified will be listed.
    It is an intersection of the tags and machines.
    """
    machines = list_tagged_machines(flake_path)

    if not tags:
        return list(machines.keys())

    filtered_machines = []
    for machine_id, machine_values in machines.items():
        if all(tag in machine_values["tags"] for tag in tags):
            filtered_machines.append(machine_id)

    return filtered_machines


def list_nixos_machines_by_tags(
    flake_path: str | Path, tags: list[str] | None = None
) -> None:
    for name in query_machines_by_tags(flake_path, tags):
        print(name)
