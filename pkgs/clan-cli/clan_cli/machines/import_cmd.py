import argparse
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.api import API
from clan_cli.clan.create import git_command
from clan_cli.clan_uri import FlakeId
from clan_cli.cmd import Log, run
from clan_cli.dirs import clan_templates, get_clan_flake_toplevel_or_env
from clan_cli.errors import ClanError
from clan_cli.machines.list import list_nixos_machines
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_command

log = logging.getLogger(__name__)


def validate_directory(root_dir: Path, machine_name: str) -> None:
    machines_dir = root_dir / "machines" / machine_name
    for root, _, files in root_dir.walk():
        for file in files:
            file_path = Path(root) / file
            if not file_path.is_relative_to(machines_dir):
                msg = f"File {file_path} is not in the 'machines/{machine_name}' directory."
                description = "Template machines are only allowed to contain files in the 'machines/{machine_name}' directory."
                raise ClanError(msg, description=description)


@dataclass
class ImportOptions:
    target: FlakeId
    src: Machine
    rename: str | None = None


@API.register
def import_machine(opts: ImportOptions) -> None:
    if not opts.target.is_local():
        msg = f"Clan {opts.target} is not a local clan."
        description = "Import machine only works on local clans"
        raise ClanError(msg, description=description)
    clan_dir = opts.target.path

    log.debug(f"Importing machine '{opts.src.name}' from {opts.src.flake}")

    if opts.src.name == opts.rename:
        msg = "Rename option must be different from the template machine name"
        raise ClanError(msg)

    if opts.src.name in list_nixos_machines(clan_dir) and not opts.rename:
        msg = f"{opts.src.name} is already defined in {clan_dir}"
        description = (
            "Please add the --rename option to import the machine with a different name"
        )
        raise ClanError(msg, description=description)

    machine_name = opts.src.name if not opts.rename else opts.rename
    dst = clan_dir / "machines" / machine_name

    if dst.exists():
        msg = f"Machine {machine_name} already exists in {clan_dir}"
        description = (
            "Please delete the existing machine or import with a different name"
        )
        raise ClanError(msg, description=description)

    with TemporaryDirectory() as tmpdir:
        tmpdirp = Path(tmpdir)
        command = nix_command(
            [
                "flake",
                "init",
                "-t",
                opts.src.get_id(),
            ]
        )
        run(command, log=Log.NONE, cwd=tmpdirp)

        validate_directory(tmpdirp, opts.src.name)
        src = tmpdirp / "machines" / opts.src.name

        if (
            not (src / "configuration.nix").exists()
            and not (src / "inventory.json").exists()
        ):
            msg = f"Template machine {opts.src.name} does not contain a configuration.nix or inventory.json"
            description = (
                "Template machine must contain a configuration.nix or inventory.json"
            )
            raise ClanError(msg, description=description)

        def log_copy(src: str, dst: str) -> None:
            relative_dst = dst.replace(f"{clan_dir}/", "")
            log.info(f"Add file: {relative_dst}")
            shutil.copy2(src, dst)

        shutil.copytree(src, dst, ignore_dangling_symlinks=True, copy_function=log_copy)

    run(git_command(clan_dir, "add", f"machines/{machine_name}"), cwd=clan_dir)

    if (dst / "inventory.json").exists():
        # TODO: Implement inventory import
        msg = "Inventory import not implemented yet"
        raise NotImplementedError(msg)
        # inventory = load_inventory_json(clan_dir)

        # inventory.machines[machine_name] = Inventory_Machine(
        #     name=machine_name,
        #     deploy=MachineDeploy(targetHost=None),
        # )
        # set_inventory(inventory, clan_dir, "Imported machine from template")


def import_command(args: argparse.Namespace) -> None:
    if args.flake:
        target = args.flake
    else:
        tmp = get_clan_flake_toplevel_or_env()
        target = FlakeId(str(tmp)) if tmp else None

    if not target:
        msg = "No clan found."
        description = (
            "Run this command in a clan directory or specify the --flake option"
        )
        raise ClanError(msg, description=description)

    src_uri = args.src
    if not src_uri:
        src_uri = FlakeId(str(clan_templates()))

    opts = ImportOptions(
        target=target,
        src=Machine(flake=src_uri, name=args.machine_name),
        rename=args.rename,
    )
    import_machine(opts)


def register_import_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "machine_name",
        type=str,
        help="The name of the machine to import",
    )
    parser.add_argument(
        "--src",
        type=FlakeId,
        help="The source flake to import the machine from",
    )
    parser.add_argument(
        "--rename",
        type=str,
        help="Rename the imported machine",
    )

    parser.set_defaults(func=import_command)
