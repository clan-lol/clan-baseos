import json
from pathlib import Path

from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import run
from clan_cli.nix import nix_build, nix_config

from .machines import Machine


# function to speedup eval if we want to evaluate all machines
def get_all_machines(flake: FlakeId, nix_options: list[str]) -> list[Machine]:
    config = nix_config()
    system = config["system"]
    json_path = run(
        nix_build([f'{flake}#clanInternals.all-machines-json."{system}"'])
    ).stdout

    machines_json = json.loads(Path(json_path.rstrip()).read_text())

    machines = []
    for name, machine_data in machines_json.items():
        machines.append(
            Machine(
                name=name,
                flake=flake,
                cached_deployment=machine_data,
                nix_options=nix_options,
            )
        )
    return machines


def get_selected_machines(
    flake: FlakeId, nix_options: list[str], machine_names: list[str]
) -> list[Machine]:
    machines = []
    for name in machine_names:
        machines.append(Machine(name=name, flake=flake, nix_options=nix_options))
    return machines
