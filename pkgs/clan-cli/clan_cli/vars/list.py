import argparse
import importlib
import logging

from ..completions import add_dynamic_completer, complete_machines
from ..machines.machines import Machine
from ._types import Var

log = logging.getLogger(__name__)


# TODO get also secret facts
def get_all_vars(machine: Machine) -> list[Var]:
    public_vars_module = importlib.import_module(machine.public_vars_module)
    public_vars_store = public_vars_module.FactStore(machine=machine)
    secret_vars_module = importlib.import_module(machine.secret_vars_module)
    secret_vars_store = secret_vars_module.SecretStore(machine=machine)
    return public_vars_store.get_all() + secret_vars_store.get_all()


def get_command(args: argparse.Namespace) -> None:
    machine = Machine(name=args.machine, flake=args.flake)

    for var in get_all_vars(machine):
        print(var)


def register_list_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to print facts for",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.set_defaults(func=get_command)
