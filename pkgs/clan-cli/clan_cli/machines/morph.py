import argparse
import json
import logging
import os
import random
import re
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import Log, RunOpts, run
from clan_cli.dirs import get_clan_flake_toplevel_or_env
from clan_cli.errors import ClanError
from clan_cli.flake import Flake
from clan_cli.inventory import Machine as InventoryMachine
from clan_cli.machines.create import CreateOptions, create_machine
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_build, nix_command
from clan_cli.vars.generate import generate_vars

log = logging.getLogger(__name__)


def is_local_input(node: dict[str, dict[str, str]]) -> bool:
    locked = node.get("locked")
    if not locked:
        return False
    # matches path and git+file://
    return (
        locked["type"] == "path"
        or re.match(r"^\w+\+file://", locked.get("url", "")) is not None
    )


def random_hostname() -> str:
    adjectives = ["wacky", "happy", "fluffy", "silly", "quirky", "zany", "bouncy"]
    nouns = ["unicorn", "penguin", "goose", "ninja", "octopus", "hamster", "robot"]
    adjective = random.choice(adjectives)
    noun = random.choice(nouns)
    return f"{adjective}-{noun}"


def morph_machine(
    flake: Flake, template_name: str, ask_confirmation: bool, name: str | None = None
) -> None:
    cmd = nix_command(
        [
            "flake",
            "archive",
            "--json",
            f"{flake}",
        ]
    )

    archive_json = run(
        cmd, RunOpts(error_msg="Failed to archive flake for morphing")
    ).stdout.rstrip()
    archive_path = json.loads(archive_json)["path"]

    with TemporaryDirectory(prefix="morph-") as temp_dir:
        flakedir = Path(temp_dir) / "flake"

        flakedir.mkdir(parents=True, exist_ok=True)
        run(["cp", "-r", archive_path + "/.", str(flakedir)])
        run(["chmod", "-R", "+w", str(flakedir)])

        os.chdir(flakedir)

        if name is None:
            name = random_hostname()

        create_opts = CreateOptions(
            template_name=template_name,
            machine=InventoryMachine(name=name),
            clan_dir=Flake(str(flakedir)),
        )
        create_machine(create_opts, commit=False)

        machine = Machine(name=name, flake=Flake(str(flakedir)))

        generate_vars([machine], generator_name=None, regenerate=False)

        machine.secret_vars_store.populate_dir(
            output_dir=Path("/run/secrets"), phases=["activation", "users", "services"]
        )

        # run(["nixos-facter", "-o", f"{flakedir}/machines/{name}/facter.json"]).stdout

        # facter_json = run(["nixos-facter"]).stdout
        # run(["cp", "facter.json", f"{flakedir}/machines/{name}/facter.json"]).stdout

        Path(f"{flakedir}/machines/{name}/facter.json").write_text(
            '{"system": "x86_64-linux"}'
        )
        result_path = run(
            nix_build(
                [f"{flakedir}#nixosConfigurations.{name}.config.system.build.toplevel"]
            )
        ).stdout.rstrip()

        ropts = RunOpts(log=Log.BOTH)

        run(
            [
                f"{result_path}/sw/bin/nixos-rebuild",
                "dry-activate",
                "--flake",
                f"{flakedir}#{name}",
            ],
            ropts,
        ).stdout.rstrip()

        if ask_confirmation:
            log.warning("ARE YOU SURE YOU WANT TO DO THIS?")
            log.warning(
                "You should have read and understood all of the above and know what you are doing."
            )

            ask = input(
                f"Do you really want convert this machine into {name}? If to continue, type in the new machine name: "
            )
            if ask != name:
                return

        run(
            [
                f"{result_path}/sw/bin/nixos-rebuild",
                "test",
                "--flake",
                f"{flakedir}#{name}",
            ],
            ropts,
        ).stdout.rstrip()


def morph_command(args: argparse.Namespace) -> None:
    if args.flake:
        clan_dir = args.flake
    else:
        tmp = get_clan_flake_toplevel_or_env()
        clan_dir = Flake(str(tmp)) if tmp else None

    if not clan_dir:
        msg = "No clan found."
        description = (
            "Run this command in a clan directory or specify the --flake option"
        )
        raise ClanError(msg, description=description)

    morph_machine(
        flake=Flake(str(args.flake)),
        template_name=args.template_name,
        ask_confirmation=args.confirm_firing,
        name=args.name,
    )


def register_morph_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=morph_command)

    parser.add_argument(
        "template_name",
        default="new-machine",
        type=str,
        help="The name of the template to use",
        nargs="?",
    )

    parser.add_argument(
        "--name",
        type=str,
        help="The name of the machine",
    )

    parser.add_argument(
        "--i-will-be-fired-for-using-this",
        dest="confirm_firing",
        default=True,
        action="store_false",
        help="Don't use unless you know what you are doing!",
    )
