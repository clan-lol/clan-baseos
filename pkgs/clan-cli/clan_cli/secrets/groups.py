import argparse
import os
from pathlib import Path

from clan_cli.completions import (
    add_dynamic_completer,
    complete_groups,
    complete_machines,
    complete_secrets,
    complete_users,
)
from clan_cli.errors import ClanError
from clan_cli.git import commit_files
from clan_cli.machines.types import machine_name_type, validate_hostname

from . import secrets
from .folders import (
    sops_groups_folder,
    sops_machines_folder,
    sops_secrets_folder,
    sops_users_folder,
)
from .sops import update_keys
from .types import (
    VALID_USER_NAME,
    group_name_type,
    secret_name_type,
    user_name_type,
)


def machines_folder(flake_dir: Path, group: str) -> Path:
    return sops_groups_folder(flake_dir) / group / "machines"


def users_folder(flake_dir: Path, group: str) -> Path:
    return sops_groups_folder(flake_dir) / group / "users"


class Group:
    def __init__(
        self, flake_dir: Path, name: str, machines: list[str], users: list[str]
    ) -> None:
        self.name = name
        self.machines = machines
        self.users = users
        self.flake_dir = flake_dir


def list_groups(flake_dir: Path) -> list[Group]:
    groups: list[Group] = []
    groups_dir = sops_groups_folder(flake_dir)
    if not groups_dir.exists():
        return groups

    for group in os.listdir(groups_dir):
        group_folder = groups_dir / group
        if not group_folder.is_dir():
            continue
        machines_path = machines_folder(flake_dir, group)
        machines = []
        if machines_path.is_dir():
            for f in machines_path.iterdir():
                if validate_hostname(f.name):
                    machines.append(f.name)
        users_path = users_folder(flake_dir, group)
        users = []
        if users_path.is_dir():
            for f in users_path.iterdir():
                if VALID_USER_NAME.match(f.name):
                    users.append(f.name)
        groups.append(Group(flake_dir, group, machines, users))
    return groups


def list_command(args: argparse.Namespace) -> None:
    for group in list_groups(args.flake.path):
        print(group.name)
        if group.machines:
            print("machines:")
            for machine in group.machines:
                print(f"  {machine}")
        if group.users:
            print("users:")
            for user in group.users:
                print(f"  {user}")
        print()


def list_directory(directory: Path) -> str:
    if not directory.exists():
        return f"{directory} does not exist"
    msg = f"\n{directory} contains:"
    for f in directory.iterdir():
        msg += f"\n  {f.name}"
    return msg


def update_group_keys(flake_dir: Path, group: str) -> list[Path]:
    updated_paths = []
    for secret_ in secrets.list_secrets(flake_dir):
        secret = sops_secrets_folder(flake_dir) / secret_
        if (secret / "groups" / group).is_symlink():
            updated_paths += update_keys(
                secret,
                secrets.collect_keys_for_path(secret),
            )
    return updated_paths


def add_member(
    flake_dir: Path, group_folder: Path, source_folder: Path, name: str
) -> list[Path]:
    source = source_folder / name
    if not source.exists():
        msg = f"{name} does not exist in {source_folder}: "
        msg += list_directory(source_folder)
        raise ClanError(msg)
    group_folder.mkdir(parents=True, exist_ok=True)
    user_target = group_folder / name
    if user_target.exists():
        if not user_target.is_symlink():
            msg = f"Cannot add user {name}. {user_target} exists but is not a symlink"
            raise ClanError(msg)
        user_target.unlink()
    user_target.symlink_to(os.path.relpath(source, user_target.parent))
    return update_group_keys(flake_dir, group_folder.parent.name)


def remove_member(flake_dir: Path, group_folder: Path, name: str) -> None:
    target = group_folder / name
    if not target.exists():
        msg = f"{name} does not exist in group in {group_folder}: "
        msg += list_directory(group_folder)
        raise ClanError(msg)
    target.unlink()

    if len(os.listdir(group_folder)) > 0:
        update_group_keys(flake_dir, group_folder.parent.name)

    if len(os.listdir(group_folder)) == 0:
        group_folder.rmdir()

    if len(os.listdir(group_folder.parent)) == 0:
        group_folder.parent.rmdir()


def add_user(flake_dir: Path, group: str, name: str) -> None:
    updated_files = add_member(
        flake_dir, users_folder(flake_dir, group), sops_users_folder(flake_dir), name
    )
    commit_files(
        updated_files,
        flake_dir,
        f"Add user {name} to group {group}",
    )


def add_user_command(args: argparse.Namespace) -> None:
    add_user(args.flake.path, args.group, args.user)


def remove_user(flake_dir: Path, group: str, name: str) -> None:
    remove_member(flake_dir, users_folder(flake_dir, group), name)


def remove_user_command(args: argparse.Namespace) -> None:
    remove_user(args.flake.path, args.group, args.user)


def add_machine(flake_dir: Path, group: str, name: str) -> None:
    updated_files = add_member(
        flake_dir,
        machines_folder(flake_dir, group),
        sops_machines_folder(flake_dir),
        name,
    )
    commit_files(
        updated_files,
        flake_dir,
        f"Add machine {name} to group {group}",
    )


def add_machine_command(args: argparse.Namespace) -> None:
    add_machine(args.flake.path, args.group, args.machine)


def remove_machine(flake_dir: Path, group: str, name: str) -> None:
    remove_member(flake_dir, machines_folder(flake_dir, group), name)


def remove_machine_command(args: argparse.Namespace) -> None:
    remove_machine(args.flake.path, args.group, args.machine)


def add_group_argument(parser: argparse.ArgumentParser) -> None:
    group_action = parser.add_argument(
        "group", help="the name of the secret", type=group_name_type
    )
    add_dynamic_completer(group_action, complete_groups)


def add_secret(flake_dir: Path, group: str, name: str) -> None:
    secrets.allow_member(
        secrets.groups_folder(sops_secrets_folder(flake_dir) / name),
        sops_groups_folder(flake_dir),
        group,
    )


def add_secret_command(args: argparse.Namespace) -> None:
    add_secret(args.flake.path, args.group, args.secret)


def remove_secret(flake_dir: Path, group: str, name: str) -> None:
    updated_paths = secrets.disallow_member(
        secrets.groups_folder(sops_secrets_folder(flake_dir) / name), group
    )
    commit_files(
        updated_paths,
        flake_dir,
        f"Remove group {group} from secret {name}",
    )


def remove_secret_command(args: argparse.Namespace) -> None:
    remove_secret(args.flake.path, args.group, args.secret)


def register_groups_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )

    # List groups
    list_parser = subparser.add_parser("list", help="list groups")
    list_parser.set_defaults(func=list_command)

    # Add user
    add_machine_parser = subparser.add_parser(
        "add-machine", help="add a machine to group"
    )
    add_group_argument(add_machine_parser)
    add_machine_action = add_machine_parser.add_argument(
        "machine", help="the name of the machines to add", type=machine_name_type
    )
    add_dynamic_completer(add_machine_action, complete_machines)
    add_machine_parser.set_defaults(func=add_machine_command)

    # Remove machine
    remove_machine_parser = subparser.add_parser(
        "remove-machine", help="remove a machine from group"
    )
    add_group_argument(remove_machine_parser)
    remove_machine_action = remove_machine_parser.add_argument(
        "machine", help="the name of the machines to remove", type=machine_name_type
    )
    add_dynamic_completer(remove_machine_action, complete_machines)
    remove_machine_parser.set_defaults(func=remove_machine_command)

    # Add user
    add_user_parser = subparser.add_parser("add-user", help="add a user to group")
    add_group_argument(add_user_parser)
    add_user_action = add_user_parser.add_argument(
        "user", help="the name of the user to add", type=user_name_type
    )
    add_dynamic_completer(add_user_action, complete_users)
    add_user_parser.set_defaults(func=add_user_command)

    # Remove user
    remove_user_parser = subparser.add_parser(
        "remove-user", help="remove a user from a group"
    )
    add_group_argument(remove_user_parser)
    remove_user_action = remove_user_parser.add_argument(
        "user", help="the name of the user to remove", type=user_name_type
    )
    add_dynamic_completer(remove_user_action, complete_users)
    remove_user_parser.set_defaults(func=remove_user_command)

    # Add secret
    add_secret_parser = subparser.add_parser(
        "add-secret", help="allow a groups to access a secret"
    )
    add_group_argument(add_secret_parser)
    add_secret_action = add_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_dynamic_completer(add_secret_action, complete_secrets)
    add_secret_parser.set_defaults(func=add_secret_command)

    # Remove secret
    remove_secret_parser = subparser.add_parser(
        "remove-secret", help="remove a group's access to a secret"
    )
    add_group_argument(remove_secret_parser)
    remove_secret_action = remove_secret_parser.add_argument(
        "secret", help="the name of the secret", type=secret_name_type
    )
    add_dynamic_completer(remove_secret_action, complete_secrets)
    remove_secret_parser.set_defaults(func=remove_secret_command)
