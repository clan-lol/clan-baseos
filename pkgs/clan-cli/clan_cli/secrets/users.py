import argparse
import json
import sys
from pathlib import Path

from clan_cli.completions import add_dynamic_completer, complete_secrets, complete_users
from clan_cli.errors import ClanError
from clan_cli.git import commit_files

from . import secrets, sops
from .folders import list_objects, remove_object, sops_secrets_folder, sops_users_folder
from .secrets import update_secrets
from .sops import read_key, write_key
from .types import (
    VALID_USER_NAME,
    public_or_private_age_key_type,
    secret_name_type,
    user_name_type,
)


def add_user(
    flake_dir: Path,
    name: str,
    key: str,
    key_type: sops.KeyType,
    force: bool,
) -> None:
    path = sops_users_folder(flake_dir) / name

    def filter_user_secrets(secret: Path) -> bool:
        return secret.joinpath("users", name).exists()

    write_key(path, key, key_type, overwrite=force)
    paths = [path]
    paths.extend(update_secrets(flake_dir, filter_secrets=filter_user_secrets))
    commit_files(
        paths,
        flake_dir,
        f"Add user {name} to secrets",
    )


def remove_user(flake_dir: Path, name: str) -> None:
    removed_paths = remove_object(sops_users_folder(flake_dir), name)
    commit_files(
        removed_paths,
        flake_dir,
        f"Remove user {name}",
    )


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
    if args.age_key or args.agekey:
        key_type = sops.KeyType.AGE
    elif args.pgp_key:
        key_type = sops.KeyType.PGP
    else:
        msg = "BUG!: key type not set"
        raise ValueError(msg)
    key = args.agekey or args.age_key or args.pgp_key
    assert key is not None, "key is None"
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
