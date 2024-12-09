import argparse
import json
import logging
import os
import shlex
import sys

from clan_cli.api import API
from clan_cli.async_run import AsyncContext, AsyncOpts, AsyncRuntime, is_async_cancelled
from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import MsgColor, RunOpts, run
from clan_cli.colors import AnsiColor
from clan_cli.completions import (
    add_dynamic_completer,
    complete_machines,
)
from clan_cli.errors import ClanError
from clan_cli.facts.generate import generate_facts
from clan_cli.facts.upload import upload_secrets
from clan_cli.inventory import Machine as InventoryMachine
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_command, nix_metadata
from clan_cli.ssh.host import Host, HostKeyCheck
from clan_cli.vars.generate import generate_vars
from clan_cli.vars.upload import upload_secret_vars

from .inventory import get_all_machines, get_selected_machines

log = logging.getLogger(__name__)


def is_path_input(node: dict[str, dict[str, str]]) -> bool:
    locked = node.get("locked")
    if not locked:
        return False
    return locked["type"] == "path" or locked.get("url", "").startswith("file://")


def upload_sources(machine: Machine) -> str:
    host = machine.build_host
    env = host.nix_ssh_env(os.environ.copy())

    flake_url = (
        str(machine.flake.path) if machine.flake.is_local() else machine.flake.url
    )
    flake_data = nix_metadata(flake_url)
    url = flake_data["resolvedUrl"]
    has_path_inputs = any(
        is_path_input(node) for node in flake_data["locks"]["nodes"].values()
    )
    if not has_path_inputs and not is_path_input(flake_data):
        # No need to upload sources, we can just build the flake url directly
        # FIXME: this might fail for private repositories?
        return url
    if not has_path_inputs:
        # Just copy the flake to the remote machine, we can substitute other inputs there.
        path = flake_data["path"]
        cmd = nix_command(
            [
                "copy",
                "--to",
                f"ssh://{host.target}",
                "--no-check-sigs",
                path,
            ]
        )
        run(
            cmd,
            RunOpts(env=env, error_msg="failed to upload sources", prefix=machine.name),
        )
        return path

    # Slow path: we need to upload all sources to the remote machine
    cmd = nix_command(
        [
            "flake",
            "archive",
            "--to",
            f"ssh://{host.target}",
            "--json",
            flake_url,
        ]
    )
    proc = run(cmd, RunOpts(env=env, error_msg="failed to upload sources"))

    try:
        return json.loads(proc.stdout)["path"]
    except (json.JSONDecodeError, OSError) as e:
        msg = f"failed to parse output of {shlex.join(cmd)}: {e}\nGot: {proc.stdout}"
        raise ClanError(msg) from e


@API.register
def update_machines(base_path: str, machines: list[InventoryMachine]) -> None:
    group_machines: list[Machine] = []

    # Convert InventoryMachine to Machine
    for machine in machines:
        name = machine.get("name")
        if not name:
            msg = "Machine name is not set"
            raise ClanError(msg)
        m = Machine(
            name,
            flake=FlakeId(base_path),
        )
        if not machine.get("deploy", {}).get("targetHost"):
            msg = f"'TargetHost' is not set for machine '{name}'"
            raise ClanError(msg)
        # Copy targetHost to machine
        m.override_target_host = machine.get("deploy", {}).get("targetHost")
        # Would be nice to have?
        # m.override_build_host = machine.deploy.buildHost
        group_machines.append(m)

    deploy_machine(group_machines)


def deploy_machine(machines: list[Machine]) -> None:
    """
    Deploy to all hosts in parallel
    """

    def deploy(machine: Machine) -> None:
        host = machine.build_host
        generate_facts([machine], service=None, regenerate=False)
        generate_vars([machine], generator_name=None, regenerate=False)

        upload_secrets(machine)
        upload_secret_vars(machine)

        path = upload_sources(
            machine=machine,
        )

        nix_options = [
            "--show-trace",
            "--fast",
            "--option",
            "keep-going",
            "true",
            "--option",
            "accept-flake-config",
            "true",
            "-L",
            "--build-host",
            "",
            *machine.nix_options,
            "--flake",
            f"{path}#{machine.name}",
        ]
        switch_cmd = ["nixos-rebuild", "switch", *nix_options]
        test_cmd = ["nixos-rebuild", "test", *nix_options]

        target_host: Host | None = host.meta.get("target_host")
        if target_host:
            switch_cmd.extend(["--target-host", target_host.target])
            test_cmd.extend(["--target-host", target_host.target])

        env = host.nix_ssh_env(None)
        ret = host.run(
            switch_cmd,
            RunOpts(check=False, msg_color=MsgColor(stderr=AnsiColor.DEFAULT)),
            extra_env=env,
        )

        if is_async_cancelled():
            return

        # if the machine is mobile, we retry to deploy with the mobile workaround method
        is_mobile = machine.deployment.get("nixosMobileWorkaround", False)
        if is_mobile and ret.returncode != 0:
            log.info("Mobile machine detected, applying workaround deployment method")
            ret = host.run(
                test_cmd,
                RunOpts(msg_color=MsgColor(stderr=AnsiColor.DEFAULT)),
                extra_env=env,
            )

        # retry nixos-rebuild switch if the first attempt failed
        elif ret.returncode != 0:
            ret = host.run(
                switch_cmd,
                RunOpts(msg_color=MsgColor(stderr=AnsiColor.DEFAULT)),
                extra_env=env,
            )

    with AsyncRuntime() as runtime:
        for machine in machines:
            machine.info(f"Updating {machine.name}")
            runtime.async_run(
                AsyncOpts(
                    tid=machine.name, async_ctx=AsyncContext(prefix=machine.name)
                ),
                deploy,
                machine,
            )
        runtime.join_all()
        runtime.check_all()


def update_command(args: argparse.Namespace) -> None:
    try:
        if args.flake is None:
            msg = "Could not find clan flake toplevel directory"
            raise ClanError(msg)
        machines = []
        if len(args.machines) == 1 and args.target_host is not None:
            machine = Machine(
                name=args.machines[0], flake=args.flake, nix_options=args.option
            )
            machine.override_target_host = args.target_host
            machine.override_build_host = args.build_host
            machine.host_key_check = HostKeyCheck.from_str(args.host_key_check)
            machines.append(machine)

        elif args.target_host is not None:
            print("target host can only be specified for a single machine")
            exit(1)
        else:
            if len(args.machines) == 0:
                ignored_machines = []
                for machine in get_all_machines(args.flake, args.option):
                    if machine.deployment.get("requireExplicitUpdate", False):
                        continue
                    try:
                        machine.build_host  # noqa: B018
                    except ClanError:  # check if we have a build host set
                        ignored_machines.append(machine)
                        continue
                    machine.host_key_check = HostKeyCheck.from_str(args.host_key_check)
                    machine.override_build_host = args.build_host
                    machines.append(machine)

                if not machines and ignored_machines != []:
                    print(
                        "WARNING: No machines to update."
                        "The following defined machines were ignored because they"
                        "do not have the `clan.core.networking.targetHost` nixos option set:",
                        file=sys.stderr,
                    )
                    for machine in ignored_machines:
                        print(machine, file=sys.stderr)

            else:
                machines = get_selected_machines(args.flake, args.option, args.machines)
                for machine in machines:
                    machine.override_build_host = args.build_host
                    machine.host_key_check = HostKeyCheck.from_str(args.host_key_check)

        deploy_machine(machines)
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(1)


def register_update_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machines",
        type=str,
        nargs="*",
        default=[],
        metavar="MACHINE",
        help="Machine to update. If no machine is specified, all machines will be updated.",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.add_argument(
        "--host-key-check",
        choices=["strict", "ask", "tofu", "none"],
        default="ask",
        help="Host key (.ssh/known_hosts) check mode.",
    )
    parser.add_argument(
        "--target-host",
        type=str,
        help="Address of the machine to update, in the format of user@host:1234.",
    )
    parser.add_argument(
        "--build-host",
        type=str,
        help="Address of the machine to build the flake, in the format of user@host:1234.",
    )
    parser.set_defaults(func=update_command)
