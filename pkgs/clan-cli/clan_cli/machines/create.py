import argparse
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.api import API
from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import Log, RunOpts, run
from clan_cli.completions import add_dynamic_completer, complete_tags
from clan_cli.dirs import TemplateType, clan_templates, get_clan_flake_toplevel_or_env
from clan_cli.errors import ClanError
from clan_cli.git import commit_file
from clan_cli.inventory import Machine as InventoryMachine
from clan_cli.inventory import (
    MachineDeploy,
    load_inventory_json,
    set_inventory,
)
from clan_cli.machines.list import list_nixos_machines
from clan_cli.nix import nix_command

log = logging.getLogger(__name__)


def validate_directory(root_dir: Path) -> None:
    machines_dir = root_dir / "machines"
    for root, _, files in root_dir.walk():
        for file in files:
            file_path = Path(root) / file
            if not file_path.is_relative_to(machines_dir):
                msg = f"File {file_path} is not in the 'machines' directory."
                log.error(msg)
                description = "Template machines are only allowed to contain files in the 'machines' directory."
                raise ClanError(msg, description=description)


@dataclass
class CreateOptions:
    clan_dir: FlakeId
    machine: InventoryMachine
    target_host: str | None = None
    template_src: FlakeId | None = None
    template_name: str | None = None


@API.register
def create_machine(opts: CreateOptions) -> None:
    if not opts.clan_dir.is_local():
        msg = f"Clan {opts.clan_dir} is not a local clan."
        description = "Import machine only works on local clans"
        raise ClanError(msg, description=description)

    if not opts.template_src:
        opts.template_src = FlakeId(str(clan_templates(TemplateType.CLAN)))

    if not opts.template_name:
        opts.template_name = "new-machine"

    clan_dir = opts.clan_dir.path

    log.debug(f"Importing machine '{opts.template_name}' from {opts.template_src}")
    machine_name = opts.machine.get("name")
    if opts.template_name in list_nixos_machines(clan_dir) and not opts.machine.get(
        "name"
    ):
        msg = f"{opts.template_name} is already defined in {clan_dir}"
        description = (
            "Please add the --rename option to import the machine with a different name"
        )
        raise ClanError(msg, description=description)

    machine_name = machine_name if machine_name else opts.template_name
    dst = clan_dir / "machines" / machine_name

    # TODO: Move this into nix code
    hostname_regex = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$"
    if not re.match(hostname_regex, machine_name):
        msg = "Machine name must be a valid hostname"
        raise ClanError(msg, location="Create Machine")

    # lopter@(2024-10-22): Could we just use warn and use the existing config?
    if dst.exists():
        msg = f"Machine {machine_name} already exists in {clan_dir}"
        description = (
            "Please delete the existing machine or import with a different name"
        )
        raise ClanError(msg, description=description)

    with TemporaryDirectory(prefix="machine-template-") as tmpdir:
        tmpdirp = Path(tmpdir)
        command = nix_command(
            [
                "flake",
                "init",
                "-t",
                f"{opts.template_src}#machineTemplates",
            ]
        )

        # Check if debug logging is enabled
        is_debug_enabled = log.isEnabledFor(logging.DEBUG)
        log_flag = Log.BOTH if is_debug_enabled else Log.NONE
        run(command, RunOpts(log=log_flag, cwd=tmpdirp))

        validate_directory(tmpdirp)

        src = tmpdirp / "machines" / opts.template_name

        if not (src / "configuration.nix").exists():
            msg = f"Template machine '{opts.template_name}' does not contain a configuration.nix"
            description = "Template machine must contain a configuration.nix"
            raise ClanError(msg, description=description)

        def log_copy(src: str, dst: str) -> None:
            relative_dst = dst.replace(f"{clan_dir}/", "")
            log.info(f"Adding file: {relative_dst}")
            shutil.copy2(src, dst)

        shutil.copytree(src, dst, ignore_dangling_symlinks=True, copy_function=log_copy)

    inventory = load_inventory_json(clan_dir)

    target_host = opts.target_host
    # TODO: We should allow the template to specify machine metadata if not defined by user
    new_machine = opts.machine
    if target_host:
        new_machine["deploy"] = {"targetHost": target_host}

    inventory["machines"] = inventory.get("machines", {})
    inventory["machines"][machine_name] = new_machine

    # Commit at the end in that order to avoid commiting halve-baked machines
    # TODO: automatic rollbacks if something goes wrong
    set_inventory(inventory, clan_dir, "Imported machine from template")

    commit_file(
        clan_dir / "machines" / machine_name,
        repo_dir=clan_dir,
        commit_message=f"Add machine {machine_name}",
    )


def create_command(args: argparse.Namespace) -> None:
    if args.flake:
        clan_dir = args.flake
    else:
        tmp = get_clan_flake_toplevel_or_env()
        clan_dir = FlakeId(str(tmp)) if tmp else None

    if not clan_dir:
        msg = "No clan found."
        description = (
            "Run this command in a clan directory or specify the --flake option"
        )
        raise ClanError(msg, description=description)

    machine = InventoryMachine(
        name=args.machine_name,
        tags=args.tags,
        deploy=MachineDeploy(),
    )
    opts = CreateOptions(
        clan_dir=clan_dir,
        machine=machine,
        template_name=args.template_name,
        target_host=args.target_host,
    )
    create_machine(opts)


def register_create_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=create_command)
    parser.add_argument(
        "machine_name",
        type=str,
        help="The name of the machine to create",
    )
    tag_parser = parser.add_argument(
        "--tags",
        nargs="+",
        default=[],
        help="Tags to associate with the machine. Can be used to assign multiple machines to services.",
    )
    add_dynamic_completer(tag_parser, complete_tags)
    parser.add_argument(
        "--template-name",
        type=str,
        help="The name of the template machine to import",
    )
    parser.add_argument(
        "--target-host",
        type=str,
        help="Address of the machine to install and update, in the format of user@host:1234",
    )
