import argparse
import re
from collections.abc import Callable
from pathlib import Path

from clan_cli.errors import ClanError

from .sops import get_public_age_key

VALID_SECRET_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")
VALID_USER_NAME = re.compile(r"^[a-z_]([a-z0-9_-]{0,31})?$")


def secret_name_type(arg_value: str) -> str:
    if not VALID_SECRET_NAME.match(arg_value):
        msg = "Invalid character in secret name. Allowed characters are a-z, A-Z, 0-9, ., -, and _"
        raise argparse.ArgumentTypeError(msg)
    return arg_value


def public_or_private_age_key_type(arg_value: str) -> str:
    if Path(arg_value).is_file():
        arg_value = Path(arg_value).read_text().strip()
    for line in arg_value.splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("age1"):
            return line.strip()
        if line.startswith("AGE-SECRET-KEY-"):
            return get_public_age_key(line)
    msg = f"Please provide an age key starting with age1 or AGE-SECRET-KEY-, got: '{arg_value}'"
    raise ClanError(msg)


def group_or_user_name_type(what: str) -> Callable[[str], str]:
    def name_type(arg_value: str) -> str:
        if len(arg_value) > 32:
            msg = f"{what.capitalize()} name must be less than 32 characters long"
            raise argparse.ArgumentTypeError(msg)
        if not VALID_USER_NAME.match(arg_value):
            msg = f"Invalid character in {what} name. Allowed characters are a-z, 0-9, -, and _. Must start with a letter or _"
            raise argparse.ArgumentTypeError(msg)
        return arg_value

    return name_type


user_name_type = group_or_user_name_type("user")
group_name_type = group_or_user_name_type("group")
