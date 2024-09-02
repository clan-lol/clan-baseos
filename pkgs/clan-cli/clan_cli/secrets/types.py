import argparse
import os
import re
from collections.abc import Callable
from pathlib import Path

from clan_cli.errors import ClanError

from .sops import get_public_key

VALID_SECRET_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")
VALID_USER_NAME = re.compile(r"^[a-z_]([a-z0-9_-]{0,31})?$")


def secret_name_type(arg_value: str) -> str:
    if not VALID_SECRET_NAME.match(arg_value):
        raise argparse.ArgumentTypeError(
            "Invalid character in secret name. Allowed characters are a-z, A-Z, 0-9, ., -, and _"
        )
    return arg_value


def public_or_private_age_key_type(arg_value: str) -> str:
    if os.path.isfile(arg_value):
        arg_value = Path(arg_value).read_text().strip()
    if arg_value.startswith("age1"):
        return arg_value.strip()
    if arg_value.startswith("AGE-SECRET-KEY-"):
        return get_public_key(arg_value)
    if not arg_value.startswith("age1"):
        raise ClanError(
            f"Please provide an age key starting with age1, got: '{arg_value}'"
        )
    return arg_value


def group_or_user_name_type(what: str) -> Callable[[str], str]:
    def name_type(arg_value: str) -> str:
        if len(arg_value) > 32:
            raise argparse.ArgumentTypeError(
                f"{what.capitalize()} name must be less than 32 characters long"
            )
        if not VALID_USER_NAME.match(arg_value):
            raise argparse.ArgumentTypeError(
                f"Invalid character in {what} name. Allowed characters are a-z, 0-9, -, and _. Must start with a letter or _"
            )
        return arg_value

    return name_type


user_name_type = group_or_user_name_type("user")
group_name_type = group_or_user_name_type("group")
