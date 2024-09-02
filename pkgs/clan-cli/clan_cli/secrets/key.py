import argparse
import logging
from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.git import commit_files

from .secrets import update_secrets
from .sops import default_sops_key_path, generate_private_key, get_public_key

log = logging.getLogger(__name__)


def extract_public_key(filepath: Path) -> str:
    """
    Extracts the public key from a given text file.
    """
    try:
        with open(filepath) as file:
            for line in file:
                # Check if the line contains the public key
                if line.startswith("# public key:"):
                    # Extract and return the public key part after the prefix
                    return line.strip().split(": ")[1]
    except FileNotFoundError:
        raise ClanError(f"The file at {filepath} was not found.")
    except Exception as e:
        raise ClanError(f"An error occurred while extracting the public key: {e}")

    raise ClanError(f"Could not find the public key in the file at {filepath}.")


def generate_key() -> str:
    path = default_sops_key_path()
    if path.exists():
        log.info(f"Key already exists at {path}")
        return extract_public_key(path)
    priv_key, pub_key = generate_private_key(out_file=path)
    log.info(
        f"Generated age private key at '{default_sops_key_path()}' for your user. Please back it up on a secure location or you will lose access to your secrets."
    )
    return pub_key


def show_key() -> str:
    return get_public_key(default_sops_key_path().read_text())


def generate_command(args: argparse.Namespace) -> None:
    pub_key = generate_key()
    log.info(
        f"Also add your age public key to the repository with: \nclan secrets users add <username> {pub_key}"
    )


def show_command(args: argparse.Namespace) -> None:
    print(show_key())


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

    parser_generate = subparser.add_parser("generate", help="generate age key")
    parser_generate.set_defaults(func=generate_command)

    parser_show = subparser.add_parser("show", help="show age public key")
    parser_show.set_defaults(func=show_command)

    parser_update = subparser.add_parser(
        "update",
        help="re-encrypt all secrets with current keys (useful when changing keys)",
    )
    parser_update.set_defaults(func=update_command)
