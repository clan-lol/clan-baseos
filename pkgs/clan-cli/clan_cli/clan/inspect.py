import argparse
from dataclasses import dataclass
from pathlib import Path

from ..cmd import run
from ..dirs import machine_gcroot
from ..errors import ClanError
from ..machines.list import list_machines
from ..machines.machines import Machine
from ..nix import nix_add_to_gcroots, nix_build, nix_config, nix_eval, nix_metadata
from ..vms.inspect import VmConfig, inspect_vm


@dataclass
class FlakeConfig:
    flake_url: str | Path
    flake_attr: str

    clan_name: str
    nar_hash: str
    icon: str | None
    description: str | None
    last_updated: str
    revision: str | None
    vm: VmConfig

    def __post_init__(self) -> None:
        if isinstance(self.vm, dict):
            self.vm = VmConfig(**self.vm)


def run_cmd(cmd: list[str]) -> str:
    proc = run(cmd)
    return proc.stdout.strip()


def inspect_flake(flake_url: str | Path, machine_name: str) -> FlakeConfig:
    config = nix_config()
    system = config["system"]

    # Check if the machine exists
    machines = list_machines(flake_url, False)
    if machine_name not in machines:
        raise ClanError(
            f"Machine {machine_name} not found in {flake_url}. Available machines: {', '.join(machines)}"
        )

    machine = Machine(machine_name, flake_url)
    vm = inspect_vm(machine)

    # Make symlink to gcroots from vm.machine_icon
    if vm.machine_icon:
        gcroot_icon: Path = machine_gcroot(flake_url=str(flake_url)) / vm.machine_name
        nix_add_to_gcroots(vm.machine_icon, gcroot_icon)

    # Get the Clan name
    cmd = nix_eval(
        [
            f'{flake_url}#clanInternals.machines."{system}"."{machine_name}".config.clan.core.clanName'
        ]
    )
    res = run_cmd(cmd)
    clan_name = res.strip('"')

    # Get the clan icon path
    cmd = nix_eval(
        [
            f'{flake_url}#clanInternals.machines."{system}"."{machine_name}".config.clan.core.clanIcon'
        ]
    )
    res = run_cmd(cmd)

    # If the icon is null, no icon is set for this Clan
    if res == "null":
        icon_path = None
    else:
        icon_path = res.strip('"')

        cmd = nix_build(
            [
                f'{flake_url}#clanInternals.machines."{system}"."{machine_name}".config.clan.core.clanIcon'
            ],
            machine_gcroot(flake_url=str(flake_url)) / "clanIcon",
        )
        run_cmd(cmd)

    # Get the flake metadata
    meta = nix_metadata(flake_url)
    return FlakeConfig(
        vm=vm,
        flake_url=flake_url,
        clan_name=clan_name,
        flake_attr=machine_name,
        nar_hash=meta["locked"]["narHash"],
        icon=icon_path,
        description=meta.get("description"),
        last_updated=meta["lastModified"],
        revision=meta.get("revision"),
    )


@dataclass
class InspectOptions:
    machine: str
    flake: Path


def inspect_command(args: argparse.Namespace) -> None:
    inspect_options = InspectOptions(
        machine=args.machine,
        flake=args.flake or Path.cwd(),
    )
    res = inspect_flake(
        flake_url=inspect_options.flake, machine_name=inspect_options.machine
    )
    print("Clan name:", res.clan_name)
    print("Icon:", res.icon)
    print("Description:", res.description)
    print("Last updated:", res.last_updated)
    print("Revision:", res.revision)


def register_inspect_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--machine", type=str, default="defaultVM")
    parser.set_defaults(func=inspect_command)
