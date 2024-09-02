import argparse
import re

VALID_HOSTNAME = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$", re.IGNORECASE)


def validate_hostname(hostname: str) -> bool:
    if len(hostname) > 63:
        return False
    return VALID_HOSTNAME.match(hostname) is not None


def machine_name_type(arg_value: str) -> str:
    if len(arg_value) > 63:
        msg = "Machine name must be less than 63 characters long"
        raise argparse.ArgumentTypeError(msg)
    if not VALID_HOSTNAME.match(arg_value):
        msg = "Invalid character in machine name. Allowed characters are a-z, 0-9, ., and -. Must not start with a number"
        raise argparse.ArgumentTypeError(msg)
    return arg_value
