# !/usr/bin/env python3
import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from clan_cli.api import API
from clan_cli.cmd import CmdOut, run
from clan_cli.dirs import clan_templates
from clan_cli.errors import ClanError
from clan_cli.inventory import Inventory, init_inventory
from clan_cli.nix import nix_command, nix_shell


@dataclass
class CreateClanResponse:
    flake_init: CmdOut
    flake_update: CmdOut
    git_init: CmdOut | None = None
    git_add: CmdOut | None = None
    git_config_username: CmdOut | None = None
    git_config_email: CmdOut | None = None


@dataclass
class CreateOptions:
    directory: Path | str
    # URL to the template to use. Defaults to the "minimal" template
    template: str = "minimal"
    setup_git: bool = True
    initial: Inventory | None = None


def git_command(directory: Path, *args: str) -> list[str]:
    return nix_shell(["nixpkgs#git"], ["git", "-C", str(directory), *args])


@API.register
def create_clan(options: CreateOptions) -> CreateClanResponse:
    directory = Path(options.directory).resolve()
    template_url = f"{clan_templates()}#{options.template}"
    if not directory.exists():
        directory.mkdir()
    else:
        # Directory already exists
        # Check if it is empty
        # Throw error otherwise
        dir_content = os.listdir(directory)
        if len(dir_content) != 0:
            raise ClanError(
                location=f"{directory.resolve()}",
                msg="Cannot create clan",
                description="Directory already exists and is not empty.",
            )

    command = nix_command(
        [
            "flake",
            "init",
            "-t",
            template_url,
        ]
    )
    flake_init = run(command, cwd=directory)

    flake_update = run(
        nix_shell(["nixpkgs#nix"], ["nix", "flake", "update"]), cwd=directory
    )

    if options.initial:
        init_inventory(str(options.directory), init=options.initial)

    response = CreateClanResponse(
        flake_init=flake_init,
        flake_update=flake_update,
    )
    if not options.setup_git:
        return response

    response.git_init = run(git_command(directory, "init"))
    response.git_add = run(git_command(directory, "add", "."))

    # check if username is set
    has_username = run(git_command(directory, "config", "user.name"), check=False)
    response.git_config_username = None
    if has_username.returncode != 0:
        response.git_config_username = run(
            git_command(directory, "config", "user.name", "clan-tool")
        )

    has_username = run(git_command(directory, "config", "user.email"), check=False)
    if has_username.returncode != 0:
        response.git_config_email = run(
            git_command(directory, "config", "user.email", "clan@example.com")
        )

    return response


def register_create_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--template",
        type=str,
        choices=["default", "minimal", "flake-parts"],
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
        "path", type=Path, help="Path to the clan directory", default=Path()
    )

    def create_flake_command(args: argparse.Namespace) -> None:
        create_clan(
            CreateOptions(
                directory=args.path,
                template=args.template,
                setup_git=not args.no_git,
            )
        )

    parser.set_defaults(func=create_flake_command)
