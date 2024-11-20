import argparse
import logging
import sys

from clan_cli.clan_uri import FlakeId
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine
from clan_cli.vars.get import get_var
from clan_cli.vars.prompt import PromptType

from .generate import Var
from .prompt import ask

log = logging.getLogger(__name__)


def set_var(
    machine: str | Machine, var: str | Var, value: bytes, flake: FlakeId
) -> None:
    if isinstance(machine, str):
        _machine = Machine(name=machine, flake=flake)
    else:
        _machine = machine
    if isinstance(var, str):
        _var = get_var(_machine, var)
    else:
        _var = var
    _var.set(value)


def set_via_stdin(machine: str, var_id: str, flake: FlakeId) -> None:
    _machine = Machine(name=machine, flake=flake)
    var = get_var(_machine, var_id)
    if sys.stdin.isatty():
        new_value = ask(var.id, PromptType.HIDDEN).encode("utf-8")
    else:
        new_value = sys.stdin.buffer.read()
    set_var(_machine, var, new_value, flake)


def _set_command(args: argparse.Namespace) -> None:
    set_via_stdin(args.machine, args.var_id, args.flake)


def register_set_parser(parser: argparse.ArgumentParser) -> None:
    machines_arg = parser.add_argument(
        "machine",
        help="The machine to set a var for",
    )
    add_dynamic_completer(machines_arg, complete_machines)

    parser.add_argument(
        "var_id",
        help="The var id for which to set the value. Example: ssh-keys/pubkey",
    )

    parser.set_defaults(func=_set_command)
