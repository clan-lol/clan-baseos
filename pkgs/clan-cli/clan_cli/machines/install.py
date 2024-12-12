import argparse
import importlib
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.api import API
from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import Log, RunOpts, run
from clan_cli.completions import (
    add_dynamic_completer,
    complete_machines,
    complete_target_host,
)
from clan_cli.errors import ClanError
from clan_cli.facts.generate import generate_facts
from clan_cli.machines.hardware import HardwareConfig
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.ssh.cli import is_ipv6, is_reachable, qrcode_scan
from clan_cli.vars.generate import generate_vars

log = logging.getLogger(__name__)


@dataclass
class InstallOptions:
    # flake to install
    flake: FlakeId
    machine: str
    target_host: str
    kexec: str | None = None
    debug: bool = False
    no_reboot: bool = False
    json_ssh_deploy: dict[str, str] | None = None
    build_on_remote: bool = False
    nix_options: list[str] = field(default_factory=list)
    update_hardware_config: HardwareConfig = HardwareConfig.NONE
    password: str | None = None


@API.register
def install_machine(opts: InstallOptions) -> None:
    machine = Machine(opts.machine, flake=opts.flake)
    machine.override_target_host = opts.target_host

    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    machine.info(f"installing {machine.name}")
    secret_facts_store = secret_facts_module.SecretStore(machine=machine)

    h = machine.target_host
    target_host = f"{h.user or 'root'}@{h.host}"
    machine.info(f"target host: {target_host}")

    generate_facts([machine])
    generate_vars([machine])

    with TemporaryDirectory(prefix="nixos-install-") as tmpdir_:
        tmpdir = Path(tmpdir_)
        upload_dir_ = machine.secrets_upload_directory

        if upload_dir_.startswith("/"):
            upload_dir_ = upload_dir_[1:]
        upload_dir = tmpdir / upload_dir_
        upload_dir.mkdir(parents=True)
        secret_facts_store.upload(upload_dir)

        if opts.password:
            os.environ["SSHPASS"] = opts.password

        cmd = [
            "nixos-anywhere",
            "--flake",
            f"{machine.flake}#{machine.name}",
            "--extra-files",
            str(tmpdir),
        ]

        if opts.no_reboot:
            cmd.append("--no-reboot")

        if opts.update_hardware_config is not HardwareConfig.NONE:
            cmd.extend(
                [
                    "--generate-hardware-config",
                    str(opts.update_hardware_config.value),
                    str(
                        opts.update_hardware_config.config_path(
                            opts.flake.path, machine.name
                        )
                    ),
                ]
            )

        if opts.password:
            cmd += [
                "--env-password",
                "--ssh-option",
                "IdentitiesOnly=yes",
            ]

        if not machine.can_build_locally or opts.build_on_remote:
            machine.info("Architecture mismatch. Building on remote machine")
            cmd.append("--build-on-remote")

        if machine.target_host.port:
            cmd += ["--ssh-port", str(machine.target_host.port)]
        if opts.kexec:
            cmd += ["--kexec", opts.kexec]
        if opts.debug:
            cmd.append("--debug")
        cmd.append(target_host)

        run(
            nix_shell(
                ["nixpkgs#nixos-anywhere"],
                cmd,
            ),
            RunOpts(log=Log.BOTH, prefix=machine.name, needs_user_terminal=True),
        )


def install_command(args: argparse.Namespace) -> None:
    try:
        if args.flake is None:
            msg = "Could not find clan flake toplevel directory"
            raise ClanError(msg)
        json_ssh_deploy = None
        if args.json:
            json_file = Path(args.json)
            if json_file.is_file():
                json_ssh_deploy = json.loads(json_file.read_text())
            else:
                json_ssh_deploy = json.loads(args.json)
        elif args.png:
            json_ssh_deploy = json.loads(qrcode_scan(args.png))

        if json_ssh_deploy:
            target_host = (
                f"root@{find_reachable_host_from_deploy_json(json_ssh_deploy)}"
            )
            password = json_ssh_deploy["pass"]
        elif args.target_host:
            target_host = args.target_host
            password = None
        else:
            machine = Machine(
                name=args.machine, flake=args.flake, nix_options=args.option
            )
            target_host = str(machine.target_host)
            password = None

        if args.password:
            password = args.password

        if not target_host:
            msg = "No target host provided, please provide a target host."
            raise ClanError(msg)

        if not args.yes:
            ask = input(f"Install {args.machine} to {target_host}? [y/N] ")
            if ask != "y":
                return None

        return install_machine(
            InstallOptions(
                flake=args.flake,
                machine=args.machine,
                target_host=target_host,
                kexec=args.kexec,
                debug=args.debug,
                no_reboot=args.no_reboot,
                json_ssh_deploy=json_ssh_deploy,
                nix_options=args.option,
                build_on_remote=args.build_on_remote,
                update_hardware_config=HardwareConfig(args.update_hardware_config),
                password=password,
            ),
        )
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(1)


def find_reachable_host_from_deploy_json(deploy_json: dict[str, str]) -> str:
    host = None
    for addr in deploy_json["addrs"]:
        if is_reachable(addr):
            host = f"[{addr}]" if is_ipv6(addr) else addr
            break
    if not host:
        msg = f"""
            Could not reach any of the host addresses provided in the json string.
            Please doublecheck if they are reachable from your machine.
            Try `ping [ADDR]` with one of the addresses: {deploy_json['addrs']}
            """
        raise ClanError(msg)
    return host


def register_install_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--kexec",
        type=str,
        help="use another kexec tarball to bootstrap NixOS",
    )
    parser.add_argument(
        "--no-reboot",
        action="store_true",
        help="do not reboot after installation",
        default=False,
    )
    parser.add_argument(
        "--build-on-remote",
        action="store_true",
        help="build the NixOS configuration on the remote machine",
        default=False,
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="do not ask for confirmation",
        default=False,
    )
    parser.add_argument(
        "--update-hardware-config",
        type=str,
        default="none",
        help="update the hardware configuration",
        choices=[x.value for x in HardwareConfig],
    )

    machines_parser = parser.add_argument(
        "machine",
        type=str,
        help="machine to install",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "-j",
        "--json",
        help="specify the json file for ssh data (generated by starting the clan installer)",
    )
    target_host_parser = group.add_argument(
        "--target-host",
        help="ssh address to install to in the form of user@host:2222",
    )
    add_dynamic_completer(target_host_parser, complete_target_host)
    parser.add_argument(
        "--password",
        help="specify the password for the ssh connection (generated by starting the clan installer)",
    )
    group.add_argument(
        "-P",
        "--png",
        help="specify the json file for ssh data as the qrcode image (generated by starting the clan installer)",
    )

    parser.set_defaults(func=install_command)
