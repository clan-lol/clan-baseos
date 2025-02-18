# !/usr/bin/env python3
import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

from clan_cli.api import API
from clan_cli.cmd import CmdOut, RunOpts, run
from clan_cli.errors import ClanError
from clan_cli.flake import Flake
from clan_cli.inventory import Inventory, init_inventory
from clan_cli.nix import nix_metadata, nix_shell
from clan_cli.templates import (
    InputPrio,
    TemplateName,
    copy_from_nixstore,
    get_template,
)

log = logging.getLogger(__name__)


@dataclass
class CreateClanResponse:
    flake_update: CmdOut | None = None
    git_init: CmdOut | None = None
    git_add: CmdOut | None = None
    git_config_username: CmdOut | None = None
    git_config_email: CmdOut | None = None


@dataclass
class CreateOptions:
    dest: Path
    template_name: str
    src_flake: Flake | None = None
    input_prio: InputPrio | None = None
    setup_git: bool = True
    initial: Inventory | None = None
    update_clan: bool = True


def git_command(directory: Path, *args: str) -> list[str]:
    return nix_shell(["nixpkgs#git"], ["git", "-C", str(directory), *args])


@API.register
def create_clan(opts: CreateOptions) -> CreateClanResponse:
    dest = opts.dest.resolve()

    if opts.src_flake is not None:
        try:
            nix_metadata(str(opts.src_flake))
        except ClanError:
            log.error(
                f"Found a repository, but it is not a valid flake: {opts.src_flake}"
            )
            log.warning("Setting src_flake to None")
            opts.src_flake = None

    template = get_template(
        TemplateName(opts.template_name),
        "clan",
        input_prio=opts.input_prio,
        clan_dir=opts.src_flake,
    )
    log.info(f"Found template '{template.name}' in '{template.input_variant}'")
    src = Path(template.src["path"])

    if dest.exists():
        dest /= src.name

    if dest.exists():
        msg = f"Destination directory {dest} already exists"
        raise ClanError(msg)

    if not src.exists():
        msg = f"Template {template} does not exist"
        raise ClanError(msg)
    if not src.is_dir():
        msg = f"Template {template} is not a directory"
        raise ClanError(msg)

    copy_from_nixstore(src, dest)

    response = CreateClanResponse()

    if opts.setup_git:
        response.git_init = run(git_command(dest, "init"))
        response.git_add = run(git_command(dest, "add", "."))

        # check if username is set
        has_username = run(
            git_command(dest, "config", "user.name"), RunOpts(check=False)
        )
        response.git_config_username = None
        if has_username.returncode != 0:
            response.git_config_username = run(
                git_command(dest, "config", "user.name", "clan-tool")
            )

        has_username = run(
            git_command(dest, "config", "user.email"), RunOpts(check=False)
        )
        if has_username.returncode != 0:
            response.git_config_email = run(
                git_command(dest, "config", "user.email", "clan@example.com")
            )

    if opts.update_clan:
        flake_update = run(
            nix_shell(["nixpkgs#nix"], ["nix", "flake", "update"]), RunOpts(cwd=dest)
        )
        response.flake_update = flake_update

    if opts.initial:
        init_inventory(str(opts.dest), init=opts.initial)

    return response


def register_create_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        type=str,
        help="""Flake input name to use as template source
        can be specified multiple times, inputs are tried in order of definition
        Example: --input clan --input clan-core
        """,
        action="append",
        default=[],
    )

    parser.add_argument(
        "--no-self",
        help="Do not look into own flake for templates",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--template",
        type=str,
        help="Clan template name",
        default="default",
    )

    parser.add_argument(
        "--no-git",
        help="Do not setup git",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "path",
        type=Path,
        help="Path where to write the clan template to",
        default=Path(),
    )

    def create_flake_command(args: argparse.Namespace) -> None:
        if len(args.input) == 0:
            args.input = ["clan", "clan-core"]

        if args.no_self:
            input_prio = InputPrio.try_inputs(tuple(args.input))
        else:
            input_prio = InputPrio.try_self_then_inputs(tuple(args.input))

        create_clan(
            CreateOptions(
                input_prio=input_prio,
                dest=args.path,
                template_name=args.template,
                setup_git=not args.no_git,
                src_flake=args.flake,
            )
        )

    parser.set_defaults(func=create_flake_command)
