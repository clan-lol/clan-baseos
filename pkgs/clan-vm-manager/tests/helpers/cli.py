import logging
import shlex

from clan_cli.custom_logger import get_caller
from clan_vm_manager import main

log = logging.getLogger(__name__)


class Cli:
    def run(self, args: list[str]) -> None:
        cmd = shlex.join(["clan", *args])
        log.debug(f"$ {cmd} \nCaller: {get_caller()}")
        main(args)
