import argparse
import json
import logging
import sys

from clan_cli.errors import ClanError
from clan_cli.git import commit_files

from . import sops
from .secrets import update_secrets
from .sops import (
    default_admin_private_key_path,
    generate_private_key,
    maybe_get_admin_public_key,
)

log = logging.getLogger(__name__)


def generate_key() -> sops.SopsKey:
    key = maybe_get_admin_public_key()
    if key is not None:
        print(f"{key.key_type.name} key {key.pubkey} is already set")
        return key

    path = default_admin_private_key_path()
    _, pub_key = generate_private_key(out_file=path)
    print(
        f"Generated age private key at '{path}' for your user. Please back it up on a secure location or you will lose access to your secrets."
    )
    return sops.SopsKey(pub_key, username="", key_type=sops.KeyType.AGE)


def generate_command(args: argparse.Namespace) -> None:
    key = generate_key()
    print("Also add your age public key to the repository with:")
    key_type = key.key_type.name.lower()
    print(f"clan secrets users add --{key_type}-key <username>")


def show_command(args: argparse.Namespace) -> None:
    key = sops.maybe_get_admin_public_key()
    if not key:
        msg = "No public key found"
        raise ClanError(msg)
    json.dump(key.as_dict(), sys.stdout, indent=2, sort_keys=True)


def update_command(args: argparse.Namespace) -> None:
    flake_dir = args.flake.path
    commit_files(update_secrets(flake_dir), flake_dir, "Updated secrets with new keys.")


def register_key_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )

    parser_generate = subparser.add_parser(
        "generate",
        description=(
            "Generate an age key for the Clan, if you already have an age "
            "or PGP key, then use it to create your user, see: "
            "`clan secrets users add --help'"
        ),
    )
    parser_generate.set_defaults(func=generate_command)

    parser_show = subparser.add_parser("show", help="show public key")
    parser_show.set_defaults(func=show_command)

    parser_update = subparser.add_parser(
        "update",
        help="re-encrypt all secrets with current keys (useful when changing keys)",
    )
    parser_update.set_defaults(func=update_command)
