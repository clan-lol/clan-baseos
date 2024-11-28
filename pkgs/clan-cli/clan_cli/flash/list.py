import argparse
import logging
import os
from pathlib import Path

from clan_cli.api import API
from clan_cli.cmd import Log, RunOpts, run
from clan_cli.errors import ClanError
from clan_cli.nix import nix_build

log = logging.getLogger(__name__)


@API.register
def list_possible_languages() -> list[str]:
    cmd = nix_build(["nixpkgs#glibcLocales"])
    result = run(cmd, RunOpts(log=Log.STDERR, error_msg="Failed to find glibc locales"))
    locale_file = Path(result.stdout.strip()) / "share" / "i18n" / "SUPPORTED"

    if not locale_file.exists():
        msg = f"Locale file '{locale_file}' does not exist."
        raise ClanError(msg)

    with locale_file.open() as f:
        lines = f.readlines()

    languages = []
    for line in lines:
        if line.startswith("#"):
            continue
        if "SUPPORTED-LOCALES" in line:
            continue
        # Split by '/' and take the first part
        language = line.split("/")[0].strip()
        languages.append(language)

    return languages


@API.register
def list_possible_keymaps() -> list[str]:
    cmd = nix_build(["nixpkgs#kbd"])
    result = run(cmd, RunOpts(log=Log.STDERR, error_msg="Failed to find kbdinfo"))
    keymaps_dir = Path(result.stdout.strip()) / "share" / "keymaps"

    if not keymaps_dir.exists():
        msg = f"Keymaps directory '{keymaps_dir}' does not exist."
        raise ClanError(msg)

    keymap_files = []

    for _root, _, files in os.walk(keymaps_dir):
        for file in files:
            if file.endswith(".map.gz"):
                # Remove '.map.gz' ending
                name_without_ext = file[:-7]
                keymap_files.append(name_without_ext)

    return keymap_files


def list_command(args: argparse.Namespace) -> None:
    if args.cmd == "languages":
        languages = list_possible_languages()
        for language in languages:
            print(language)
    elif args.cmd == "keymaps":
        keymaps = list_possible_keymaps()
        for keymap in keymaps:
            print(keymap)


def register_flash_list_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "cmd",
        choices=["languages", "keymaps"],
        type=str,
        help="list possible languages or keymaps",
    )

    parser.set_defaults(func=list_command)
