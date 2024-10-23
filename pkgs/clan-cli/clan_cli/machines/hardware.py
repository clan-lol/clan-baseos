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
    backend: Literal["nixos-generate-config", "nixos-facter"]


hw_nix_file = "hardware-configuration.nix"
facter_file = "facter.json"


@API.register
def show_machine_hardware_info(
    clan_dir: Path, machine_name: str
) -> HardwareReport | None:
    """
    Show hardware information for a machine returns None if none exist.
    """

    hw_file = Path(clan_dir) / "machines" / machine_name / hw_nix_file
    is_template = hw_file.exists() and "throw" in hw_file.read_text()

    if hw_file.exists() and not is_template:
        return HardwareReport("nixos-generate-config")

    if Path(f"{clan_dir}/machines/{machine_name}/{facter_file}").exists():
        return HardwareReport("nixos-facter")

    return None


@API.register
def show_machine_deployment_target(clan_dir: Path, machine_name: str) -> str | None:
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
def show_machine_hardware_platform(clan_dir: Path, machine_name: str) -> str | None:
    """
    Show hardware information for a machine returns None if none exist.
    """
    config = nix_config()
    system = config["system"]
    cmd = nix_eval(
        [
            f"{clan_dir}#clanInternals.machines.{system}.{machine_name}",
            "--apply",
            "machine: { inherit (machine.pkgs) system; }",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)
    res = proc.stdout.strip()

    host_platform = json.loads(res)
    return host_platform.get("system", None)


@dataclass
class HardwareGenerateOptions:
    flake: FlakeId
    machine: str
    backend: Literal["nixos-generate-config", "nixos-facter"]
    target_host: str | None = None
    keyfile: str | None = None
    password: str | None = None


@API.register
def generate_machine_hardware_info(opts: HardwareGenerateOptions) -> HardwareReport:
    """
    Generate hardware information for a machine
    and place the resulting *.nix file in the machine's directory.
    """

    machine = Machine(opts.machine, flake=opts.flake)
    if opts.target_host is not None:
        machine.override_target_host = opts.target_host

    hw_file = opts.flake.path / "machines" / opts.machine
    if opts.backend == "nixos-generate-config":
        hw_file /= hw_nix_file
    else:
        hw_file /= facter_file

    hw_file.parent.mkdir(parents=True, exist_ok=True)

    if opts.backend == "nixos-facter":
        config_command = ["nixos-facter"]
    else:
        config_command = [
            "nixos-generate-config",
            # Filesystems are managed by disko
            "--no-filesystems",
            "--show-hardware-config",
        ]

    host = machine.target_host
    target_host = f"{host.user or 'root'}@{host.host}"
    cmd = nix_shell(
        [
            "nixpkgs#openssh",
            "nixpkgs#sshpass",
        ],
        [
            *(["sshpass", "-p", opts.password] if opts.password else []),
            "ssh",
            *(["-i", f"{opts.keyfile}"] if opts.keyfile else []),
            # Disable known hosts file
            "-o",
            "UserKnownHostsFile=/dev/null",
            # Disable strict host key checking. The GUI user cannot type "yes" into the ssh terminal.
            "-o",
            "StrictHostKeyChecking=accept-new",
            *(
                ["-p", str(machine.target_host.port)]
                if machine.target_host.port
                else []
            ),
            target_host,
            *config_command,
        ],
    )
    out = run(cmd, needs_user_terminal=True)
    if out.returncode != 0:
        log.error(out)
        msg = f"Failed to inspect {opts.machine}. Address: {opts.target_host}"
        raise ClanError(msg)

    backup_file = None
    if hw_file.exists():
        backup_file = hw_file.with_suffix(".bak")
        hw_file.replace(backup_file)
    hw_file.write_text(out.stdout)
    print(f"Successfully generated: {hw_file}")

    # try to evaluate the machine
    # If it fails, the hardware-configuration.nix file is invalid

    commit_file(
        hw_file,
        opts.flake.path,
        f"machines/{opts.machine}/{hw_file.name}: update hardware configuration",
    )
    try:
        show_machine_hardware_platform(opts.flake.path, opts.machine)
    except ClanCmdError as e:
        log.exception("Failed to evaluate hardware-configuration.nix")
        # Restore the backup file
        print(f"Restoring backup file {backup_file}")
        if backup_file:
            backup_file.replace(hw_file)
        # TODO: Undo the commit

        msg = "Invalid hardware-configuration.nix file"
        raise ClanError(
            msg,
            description=f"Configuration at '{hw_file}' is invalid. Please check the file and try again.",
        ) from e

    return HardwareReport(opts.backend)


def update_hardware_config_command(args: argparse.Namespace) -> None:
    opts = HardwareGenerateOptions(
        flake=args.flake,
        machine=args.machine,
        target_host=args.target_host,
        password=args.password,
        backend=args.backend,
    )
    generate_machine_hardware_info(opts)


def register_update_hardware_config(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=update_hardware_config_command)
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
        "--backend",
        help="The type of hardware report to generate.",
        choices=["nixos-generate-config", "nixos-facter"],
        default="nixos-generate-config",
    )
    add_dynamic_completer(machine_parser, complete_machines)
