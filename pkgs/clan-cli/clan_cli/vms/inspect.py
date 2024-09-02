import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from clan_cli.clan_uri import FlakeId
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine


@dataclass
class WaypipeConfig:
    enable: bool
    command: list[str]


@dataclass
class VmConfig:
    machine_name: str
    machine_icon: Path
    machine_description: str
    flake_url: FlakeId
    clan_name: str

    cores: int
    memory_size: int
    graphics: bool
    waypipe: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.flake_url, str):
            self.flake_url = FlakeId(self.flake_url)
        if isinstance(self.waypipe, dict):
            self.waypipe = WaypipeConfig(**self.waypipe)
        if isinstance(self.flake_url, dict):
            self.flake_url = FlakeId(**self.flake_url)


def inspect_vm(machine: Machine) -> VmConfig:
    data = json.loads(machine.eval_nix("config.clan.core.vm.inspect"))
    return VmConfig(flake_url=machine.flake, **data)


@dataclass
class InspectOptions:
    machine: str
    flake: FlakeId


def inspect_command(args: argparse.Namespace) -> None:
    inspect_options = InspectOptions(
        machine=args.machine,
        flake=args.flake or FlakeId(str(Path.cwd())),
    )

    machine = Machine(inspect_options.machine, inspect_options.flake)
    res = inspect_vm(machine)
    print("Cores:", res.cores)
    print("Memory size:", res.memory_size)
    print("Graphics:", res.graphics)


def register_inspect_parser(parser: argparse.ArgumentParser) -> None:
    machine_action = parser.add_argument("machine", type=str, default="defaultVM")
    add_dynamic_completer(machine_action, complete_machines)
    parser.set_defaults(func=inspect_command)
