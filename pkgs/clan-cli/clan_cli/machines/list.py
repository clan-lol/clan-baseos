import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from clan_cli.api import API
from clan_cli.api.disk import MachineDiskMatter
from clan_cli.api.modules import parse_frontmatter
from clan_cli.api.serde import dataclass_to_dict
from clan_cli.cmd import RunOpts, run_no_stdout
from clan_cli.completions import add_dynamic_completer, complete_tags
from clan_cli.dirs import specific_machine_dir
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.inventory import (
    Machine,
    load_inventory_eval,
    patch_inventory_with,
)
from clan_cli.machines.hardware import HardwareConfig
from clan_cli.nix import nix_eval, nix_shell
from clan_cli.tags import list_nixos_machines_by_tags

log = logging.getLogger(__name__)


@API.register
def set_machine(flake_url: Path, machine_name: str, machine: Machine) -> None:
    patch_inventory_with(
        flake_url, f"machines.{machine_name}", dataclass_to_dict(machine)
    )


@API.register
def list_inventory_machines(flake_url: str | Path) -> dict[str, Machine]:
    inventory = load_inventory_eval(flake_url)
    return inventory.get("machines", {})


@dataclass
class MachineDetails:
    machine: Machine
    hw_config: HardwareConfig | None = None
    disk_schema: MachineDiskMatter | None = None


import re


def extract_header(c: str) -> str:
    header_lines = []
    for line in c.splitlines():
        match = re.match(r"^\s*#(.*)", line)
        if match:
            header_lines.append(match.group(1).strip())
        else:
            break  # Stop once the header ends
    return "\n".join(header_lines)


@API.register
def get_inventory_machine_details(flake_url: Path, machine_name: str) -> MachineDetails:
    inventory = load_inventory_eval(flake_url)
    machine = inventory.get("machines", {}).get(machine_name)
    if machine is None:
        msg = f"Machine {machine_name} not found in inventory"
        raise ClanError(msg)

    hw_config = HardwareConfig.detect_type(flake_url, machine_name)

    machine_dir = specific_machine_dir(flake_url, machine_name)
    disk_schema: MachineDiskMatter | None = None
    disk_path = machine_dir / "disko.nix"
    if disk_path.exists():
        with disk_path.open() as f:
            content = f.read()
            header = extract_header(content)
            data, _rest = parse_frontmatter(header)
            if data:
                disk_schema = data  # type: ignore

    return MachineDetails(machine=machine, hw_config=hw_config, disk_schema=disk_schema)


def list_nixos_machines(flake_url: str | Path) -> list[str]:
    cmd = nix_eval(
        [
            f"{flake_url}#clanInternals.machines.x86_64-linux",
            "--apply",
            "builtins.attrNames",
            "--json",
        ]
    )

    proc = run_no_stdout(cmd)

    try:
        res = proc.stdout.strip()
        data = json.loads(res)
    except json.JSONDecodeError as e:
        msg = f"Error decoding machines from flake: {e}"
        raise ClanError(msg) from e
    else:
        return data


@dataclass
class ConnectionOptions:
    keyfile: str | None = None
    timeout: int = 2


@API.register
def check_machine_online(
    flake_url: str | Path, machine_name: str, opts: ConnectionOptions | None
) -> Literal["Online", "Offline"]:
    machine = load_inventory_eval(flake_url).get("machines", {}).get(machine_name)
    if not machine:
        msg = f"Machine {machine_name} not found in inventory"
        raise ClanError(msg)

    hostname = machine.get("deploy", {}).get("targetHost")

    if not hostname:
        msg = f"Machine {machine_name} does not specify a targetHost"
        raise ClanError(msg)

    timeout = opts.timeout if opts and opts.timeout else 20

    cmd = nix_shell(
        ["nixpkgs#util-linux", *(["nixpkgs#openssh"] if hostname else [])],
        [
            "ssh",
            *(["-i", f"{opts.keyfile}"] if opts and opts.keyfile else []),
            # Disable strict host key checking
            "-o",
            "StrictHostKeyChecking=accept-new",
            # Disable known hosts file
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            f"ConnectTimeout={timeout}",
            f"{hostname}",
            "true",
            "&> /dev/null",
        ],
    )
    try:
        proc = run_no_stdout(cmd, RunOpts(needs_user_terminal=True))
        if proc.returncode != 0:
            return "Offline"
    except ClanCmdError:
        return "Offline"
    else:
        return "Online"


def list_command(args: argparse.Namespace) -> None:
    flake_path = args.flake.path
    if args.tags:
        list_nixos_machines_by_tags(flake_path, args.tags)
        return
    for name in list_nixos_machines(flake_path):
        print(name)


def register_list_parser(parser: argparse.ArgumentParser) -> None:
    tag_parser = parser.add_argument(
        "--tags",
        nargs="+",
        default=[],
        help="Tags that machines should be queried for. Multiple tags will intersect.",
    )
    add_dynamic_completer(tag_parser, complete_tags)
    parser.set_defaults(func=list_command)
