import argparse
import logging
import os

from clan_cli.errors import ClanError
from clan_cli.flake import Flake
from clan_cli.secrets.key import generate_key
from clan_cli.secrets.sops import KeyType, maybe_get_admin_public_key
from clan_cli.secrets.users import add_user

log = logging.getLogger(__name__)


def keygen(user: str | None, flake: Flake, force: bool) -> None:
    if user is None:
        user = os.getenv("USER", None)
        if not user:
            msg = "No user provided and $USER is not set. Please provide a user via --user."
            raise ClanError(msg)
    pub_key = maybe_get_admin_public_key()
    if not pub_key:
        pub_key = generate_key()
    # TODO set flake_dir=flake.path / "vars"
    add_user(
        flake_dir=flake.path,
        name=user,
        key=pub_key.pubkey,
        key_type=KeyType.AGE,
        force=force,
    )


def _command(
    args: argparse.Namespace,
) -> None:
    keygen(
        user=args.user,
        flake=args.flake,
        force=args.force,
    )


def register_keygen_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--user",
        help="The user to generate the keys for. Default: $USER",
        default=None,
    )

    parser.add_argument(
        "-f", "--force", help="overwrite existing user", action="store_true"
    )

    parser.set_defaults(func=_command)
