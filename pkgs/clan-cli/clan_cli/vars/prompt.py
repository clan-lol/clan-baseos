import logging
import sys
from getpass import getpass

from clan_cli.errors import ClanError

log = logging.getLogger(__name__)


def ask(description: str, input_type: str) -> str:
    if input_type == "line":
        result = input(f"Enter the value for {description}: ")
    elif input_type == "multiline":
        print(f"Enter the value for {description} (Finish with Ctrl-D): ")
        result = sys.stdin.read()
    elif input_type == "hidden":
        result = getpass(f"Enter the value for {description} (hidden): ")
    else:
        msg = f"Unknown input type: {input_type} for prompt {description}"
        raise ClanError(msg)
    log.info("Input received. Processing...")
    return result
