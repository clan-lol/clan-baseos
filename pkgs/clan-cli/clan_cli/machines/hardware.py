import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from clan_cli.api import API
from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import run, run_no_stdout
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.git import commit_file
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_config, nix_eval, nix_shell

from .types import machine_name_type

log = logging.getLogger(__name__)


@dataclass
class HardwareReport:
    file: Literal["nixos-generate-config", "nixos-facter"]


hw_nix_file = "hardware-configuration.nix"
facter_file = "facter.json"


@API.register
def show_machine_hardware_info(
    clan_dir: str | Path, machine_name: str
) -> HardwareReport | None:
    """
    Show hardware information for a machine returns None if none exist.
    """

    hw_file = Path(f"{clan_dir}/machines/{machine_name}/{hw_nix_file}")
    is_template = hw_file.exists() and "throw" in hw_file.read_text()

    if hw_file.exists() and not is_template:
        return HardwareReport("nixos-generate-config")

    if Path(f"{clan_dir}/machines/{machine_name}/{facter_file}").exists():
        return HardwareReport("nixos-facter")

    return None


@API.register
def show_machine_deployment_target(
    clan_dir: str | Path, machine_name: str
) -> str | None:
    """
    Show deployment target for a machine returns None if none exist.
    """
    config = nix_config()
    system = config["system"]
    cmd = nix_eval(
        [
            f"{clan_dir}#clanInternals.machines.{system}.{machine_name}",
            "--apply",
            "machine: { inherit (machine.config.clan.core.networking) targetHost; }",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)
    res = proc.stdout.strip()

    target_host = json.loads(res)
    return target_host.get("targetHost", None)


@API.register
def show_machine_hardware_platform(
    clan_dir: str | Path, machine_name: str
) -> str | None:
    """
    Show hardware information for a machine returns None if none exist.
    """
    config = nix_config()
    system = config["system"]
    cmd = nix_eval(
        [
            f"{clan_dir}#clanInternals.machines.{system}.{machine_name}",
            "--apply",
            "machine: { inherit (machine.config.nixpkgs.hostPlatform) system; }",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)
    res = proc.stdout.strip()

    host_platform = json.loads(res)
    return host_platform.get("system", None)


@API.register
def generate_machine_hardware_info(
    clan_dir: FlakeId,
    machine_name: str,
    hostname: str | None = None,
    password: str | None = None,
    keyfile: str | None = None,
    force: bool | None = False,
    report_type: Literal[
        "nixos-generate-config", "nixos-facter"
    ] = "nixos-generate-config",
) -> HardwareReport:
    """
    Generate hardware information for a machine
    and place the resulting *.nix file in the machine's directory.
    """

    machine = Machine(machine_name, flake=clan_dir)
    if hostname is not None:
        machine.target_host_address = hostname

    nixos_generate_cmd = [
        "nixos-generate-config",  # Filesystems are managed by disko
        "--no-filesystems",
        "--show-hardware-config",
    ]

    nixos_facter_cmd = ["nix", "run", "--refresh", "github:numtide/nixos-facter"]

    host = machine.target_host
    target_host = f"{host.user or 'root'}@{host.host}"
    cmd = nix_shell(
        [
            "nixpkgs#openssh",
            "nixpkgs#sshpass",
        ],
        [
            *(["sshpass", "-p", f"{password}"] if password else []),
            "ssh",
            *(["-i", f"{keyfile}"] if keyfile else []),
            # Disable known hosts file
            "-o",
            "UserKnownHostsFile=/dev/null",
            # Disable strict host key checking. The GUI user cannot type "yes" into the ssh terminal.
            "-o",
            "StrictHostKeyChecking=no",
            *(
                ["-p", str(machine.target_host.port)]
                if machine.target_host.port
                else []
            ),
            target_host,
            *(
                nixos_generate_cmd
                if report_type == "nixos-generate-config"
                else nixos_facter_cmd
            ),
        ],
    )
    out = run(cmd)
    if out.returncode != 0:
        log.error(f"Failed to inspect {machine_name}. Address: {hostname}")
        log.error(out)
        msg = f"Failed to inspect {machine_name}. Address: {hostname}"
        raise ClanError(msg)

    hw_file = Path(
        f"{clan_dir}/machines/{machine_name}/{hw_nix_file if report_type == 'nixos-generate-config' else facter_file}"
    )
    hw_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if the hardware-configuration.nix file is a template
    is_template = hw_file.exists() and "throw" in hw_file.read_text()

    if hw_file.exists() and not force and not is_template:
        msg = "File exists."
        raise ClanError(
            msg,
            description="Hardware file already exists. To force overwrite the existing configuration use '--force'.",
            location=f"{__name__} {hw_file}",
        )

    backup_file = None
    if hw_file.exists() and force:
        # Backup the existing file
        backup_file = hw_file.with_suffix(".bak")
        hw_file.replace(backup_file)
        print(f"Backed up existing {hw_file} to {backup_file}")

    with hw_file.open("w") as f:
        f.write(out.stdout)
        print(f"Successfully generated: {hw_file}")

    # try to evaluate the machine
    # If it fails, the hardware-configuration.nix file is invalid

    commit_file(
        hw_file,
        clan_dir.path,
        f"HW/report: Hardware configuration for {machine_name}",
    )
    try:
        show_machine_hardware_platform(clan_dir, machine_name)
    except ClanCmdError as e:
        log.error(e)
        # Restore the backup file
        print(f"Restoring backup file {backup_file}")
        if backup_file:
            backup_file.replace(hw_file)
        # TODO: Undo the commit

        msg = "Invalid hardware-configuration.nix file"
        raise ClanError(
            msg,
            description="The hardware-configuration.nix file is invalid. Please check the file and try again.",
            location=f"{__name__} {hw_file}",
        ) from e

    return HardwareReport(report_type)


@dataclass
class HardwareGenerateOptions:
    flake: FlakeId
    machine: str
    target_host: str | None
    password: str | None
    force: bool | None


def hw_generate_command(args: argparse.Namespace) -> None:
    opts = HardwareGenerateOptions(
        flake=args.flake,
        machine=args.machine,
        target_host=args.target_host,
        password=args.password,
        force=args.force,
    )
    hw_info = generate_machine_hardware_info(
        opts.flake, opts.machine, opts.target_host, opts.password, opts.force
    )
    print("Successfully generated hardware information.")
    print(f"Target: {opts.machine} ({opts.target_host})")
    print(f"Type: {hw_info.file}")


def register_hw_generate(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=hw_generate_command)
    machine_parser = parser.add_argument(
        "machine",
        help="the name of the machine",
        type=machine_name_type,
    )
    machine_parser = parser.add_argument(
        "target_host",
        type=str,
        nargs="?",
        help="ssh address to install to in the form of user@host:2222",
    )
    machine_parser = parser.add_argument(
        "--password",
        help="Pre-provided password the cli will prompt otherwise if needed.",
        type=str,
        required=False,
    )
    machine_parser = parser.add_argument(
        "--force",
        help="Will overwrite the hardware-configuration.nix file.",
        action="store_true",
    )
    add_dynamic_completer(machine_parser, complete_machines)
