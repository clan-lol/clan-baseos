import argparse
import importlib
import logging

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

from ._types import Var

log = logging.getLogger(__name__)


# TODO get also secret facts
def all_vars(machine: Machine) -> list[Var]:
    public_vars_module = importlib.import_module(machine.public_vars_module)
    public_vars_store = public_vars_module.FactStore(machine=machine)
    secret_vars_module = importlib.import_module(machine.secret_vars_module)
    secret_vars_store = secret_vars_module.SecretStore(machine=machine)
    return public_vars_store.get_all() + secret_vars_store.get_all()


def stringify_vars(_vars: list[Var]) -> str:
    return "\n".join([str(var) for var in _vars])


def stringify_all_vars(machine: Machine) -> str:
    return stringify_vars(all_vars(machine))


def list_command(args: argparse.Namespace) -> None:
    machine = Machine(name=args.machine, flake=args.flake)
    print(stringify_all_vars(machine))


def register_list_parser(parser: argparse.ArgumentParser) -> None:
    machines_arg = parser.add_argument(
        "machine",
        help="The machine to print vars for",
    )
    add_dynamic_completer(machines_arg, complete_machines)

    parser.set_defaults(func=list_command)
