import argparse
import json
import logging
import os
import sys
from pathlib import Path

from clan_cli.completions import add_dynamic_completer, complete_secrets, complete_users
from clan_cli.errors import ClanError
from clan_cli.git import commit_files

from . import groups, secrets, sops
from .folders import (
    list_objects,
    remove_object,
    sops_groups_folder,
    sops_secrets_folder,
    sops_users_folder,
)
from .secrets import update_secrets
from .sops import read_key, write_key
from .types import (
    VALID_USER_NAME,
    public_or_private_age_key_type,
    secret_name_type,
    user_name_type,
)

log = logging.getLogger(__name__)


def add_user(
    flake_dir: Path,
    name: str,
    key: str,
    key_type: sops.KeyType,
    force: bool,
) -> None:
    path = sops_users_folder(flake_dir) / name

    groupnames = [p.name for p in groups.get_groups(flake_dir, "users", name)]

    def filter_user_secrets(secret: Path) -> bool:
        if secret.joinpath("users", name).exists():
            return True
        return any(secret.joinpath("groups", name).exists() for name in groupnames)

    write_key(path, key, key_type, overwrite=force)
    paths = [path]

    paths.extend(update_secrets(flake_dir, filter_secrets=filter_user_secrets))
    commit_files(
        paths,
        flake_dir,
        f"Add user {name} to secrets",
    )


def remove_user(flake_dir: Path, name: str) -> None:
    updated_paths: list[Path] = []
    # Remove the user from any group where it belonged:
    groups_dir = sops_groups_folder(flake_dir)
    if groups_dir.exists():
        for group in os.listdir(groups_dir):
            group_folder = groups_dir / group
            if not group_folder.is_dir():
                continue
            memberships = group_folder / "users"
            if not (memberships / name).exists():
                continue
            log.info(f"Removing user {name} from group {group}")
            updated_paths.extend(
                groups.remove_member(flake_dir, group, groups.users_folder, name)
            )
    # Remove the user's key:
    updated_paths.extend(remove_object(sops_users_folder(flake_dir), name))
    # Remove the user from any secret where it was used:
    updated_paths.extend(update_secrets(flake_dir))
    commit_files(updated_paths, flake_dir, f"Remove user {name}")


def get_user(flake_dir: Path, name: str) -> sops.SopsKey:
    key, key_type = read_key(sops_users_folder(flake_dir) / name)
    return sops.SopsKey(key, name, key_type)


def list_users(flake_dir: Path) -> list[str]:
    path = sops_users_folder(flake_dir)

    def validate(name: str) -> bool:
        return (
            VALID_USER_NAME.match(name) is not None
            and (path / name / "key.json").exists()
        )

    return list_objects(path, validate)


def add_secret(flake_dir: Path, user: str, secret: str) -> None:
    updated_paths = secrets.allow_member(
        secrets.users_folder(sops_secrets_folder(flake_dir) / secret),
        sops_users_folder(flake_dir),
        user,
    )
    commit_files(
        updated_paths,
        flake_dir,
        f"Add {user} to secret",
    )


def remove_secret(flake_dir: Path, user: str, secret: str) -> None:
    updated_paths = secrets.disallow_member(
        secrets.users_folder(sops_secrets_folder(flake_dir) / secret), user
    )
    commit_files(
        updated_paths,
        flake_dir,
        f"Remove {user} from secret",
    )


def list_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    lst = list_users(args.flake.path)
    if len(lst) > 0:
        print("\n".join(lst))


def add_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    keys_args = (args.age_key, args.agekey, args.pgp_key)
    keys_count = sum(1 if key else 0 for key in keys_args)
    if keys_count != 1:
        err_msg = (
            f"Please provide one key (got {keys_count}) through `--pgp-key`, "
            f"`--age-key`, or as a positional (age key) argument."
        )
        raise ClanError(err_msg)
    if args.age_key or args.agekey:
        key_type = sops.KeyType.AGE
    else:
        key_type = sops.KeyType.PGP
    key = args.agekey or args.age_key or args.pgp_key
    add_user(args.flake.path, args.user, key, key_type, args.force)


def get_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    key = get_user(args.flake.path, args.user)
    json.dump(key.as_dict(), sys.stdout, indent=2, sort_keys=True)


def remove_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    remove_user(args.flake.path, args.user)


def add_secret_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    add_secret(args.flake.path, args.user, args.secret)


def remove_secret_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    remove_secret(args.flake.path, args.user, args.secret)


def register_users_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )
    list_parser = subparser.add_parser("list", help="list users")
    list_parser.set_defaults(func=list_command)

    add_parser = subparser.add_parser("add", help="add a user")
    add_parser.add_argument(
        "-f", "--force", help="overwrite existing user", action="store_true"
    )
    add_parser.add_argument("user", help="the name of the user", type=user_name_type)
    key_type = add_parser.add_mutually_exclusive_group(required=True)
    key_type.add_argument(
        "agekey",
        help="public or private age key of the user. "
        "Execute 'clan secrets key --help' on how to retrieve a key. "
        "To fetch an age key from an SSH host key: ssh-keyscan <domain_name> | nix shell nixpkgs#ssh-to-age -c ssh-to-age",
        type=public_or_private_age_key_type,
        nargs="?",
    )
    key_type.add_argument(
        "--age-key",
        help="public or private age key of the user. "
        "Execute 'clan secrets key --help' on how to retrieve a key. "
        "To fetch an age key from an SSH host key: ssh-keyscan <domain_name> | nix shell nixpkgs#ssh-to-age -c ssh-to-age",
        type=public_or_private_age_key_type,
    )
    key_type.add_argument(
        "--pgp-key",
        help=(
            "public PGP encryption key of the user. "
            # Use --fingerprint --fingerprint to get fingerprints for subkeys:
            "Execute `gpg -k --fingerprint --fingerprint` and remove spaces to get it."
        ),
    )
    add_parser.set_defaults(func=add_command)

    get_parser = subparser.add_parser("get", help="get a user public key")
    get_user_action = get_parser.add_argument(
        "user", help="the name of the user", type=user_name_type
    )
    add_dynamic_completer(get_user_action, complete_users)
    get_parser.set_defaults(func=get_command)

    remove_parser = subparser.add_parser("remove", help="remove a user")
    remove_user_action = remove_parser.add_argument(
        "user", help="the name of the user", type=user_name_type
    )
    add_dynamic_completer(remove_user_action, complete_users)
    remove_parser.set_defaults(func=remove_command)

    add_secret_parser = subparser.add_parser(
        "add-secret", help="allow a user to access a secret"
    )
    add_secret_user_action = add_secret_parser.add_argument(
        "user", help="the name of the user", type=user_name_type
    )
    add_dynamic_completer(add_secret_user_action, complete_users)
    add_secrets_action = add_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_dynamic_completer(add_secrets_action, complete_secrets)
    add_secret_parser.set_defaults(func=add_secret_command)

    remove_secret_parser = subparser.add_parser(
        "remove-secret", help="remove a user's access to a secret"
    )
    remove_secret_user_action = remove_secret_parser.add_argument(
        "user", help="the name of the group", type=user_name_type
    )
    add_dynamic_completer(remove_secret_user_action, complete_users)
    remove_secrets_action = remove_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_dynamic_completer(remove_secrets_action, complete_secrets)
    remove_secret_parser.set_defaults(func=remove_secret_command)
