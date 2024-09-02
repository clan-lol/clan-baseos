import logging
import shlex

from clan_app import main
from clan_cli.custom_logger import get_caller

log = logging.getLogger(__name__)


def run(args: list[str]) -> None:
    cmd = shlex.join(["clan", *args])
    log.debug(f"$ {cmd} \nCaller: {get_caller()}")
    main(args)
