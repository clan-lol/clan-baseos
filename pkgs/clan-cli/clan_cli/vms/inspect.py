import argparse
import dataclasses
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.flake import Flake
from clan_cli.machines.machines import Machine


@dataclass
class WaypipeConfig:
    enable: bool
    command: list[str]

    @classmethod
    def from_json(cls: type["WaypipeConfig"], data: dict[str, Any]) -> "WaypipeConfig":
        return cls(
            enable=data["enable"],
            command=data["command"],
        )


@dataclass
class VmConfig:
    machine_name: str
    flake_url: Flake

    cores: int
    memory_size: int
    graphics: bool

    # FIXME: I don't think this belongs here.
    clan_name: str
    machine_description: str | None
    machine_icon: Path | None

    waypipe: WaypipeConfig

    @classmethod
    def from_json(cls: type["VmConfig"], data: dict[str, Any]) -> "VmConfig":
        return cls(
            machine_name=data["machine_name"],
            flake_url=Flake.from_json(data["flake_url"]),
            cores=data["cores"],
            memory_size=data["memory_size"],
            graphics=data["graphics"],
            clan_name=data["clan_name"],
            machine_description=data.get("machine_description"),
            machine_icon=data.get("machine_icon"),
            waypipe=WaypipeConfig.from_json(data["waypipe"]),
        )


def inspect_vm(machine: Machine) -> VmConfig:
    data = json.loads(machine.eval_nix("config.clan.core.vm.inspect"))
    # HACK!
    data["flake_url"] = dataclasses.asdict(machine.flake)
    return VmConfig.from_json(data)


@dataclass
class InspectOptions:
    machine: str
    flake: Flake


def inspect_command(args: argparse.Namespace) -> None:
    inspect_options = InspectOptions(
        machine=args.machine,
        flake=args.flake or Flake(str(Path.cwd())),
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
