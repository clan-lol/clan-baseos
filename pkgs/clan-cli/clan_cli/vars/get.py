import argparse
import logging
import sys

from clan_cli.clan_uri import FlakeId
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine

from ._types import Var
from .list import get_vars

log = logging.getLogger(__name__)


def get_var(machine: Machine, var_id: str) -> Var:
    vars_ = get_vars(machine)
    results = []
    for var in vars_:
        if var_id in var.id:
            results.append(var)
    if len(results) == 0:
        msg = f"No var found for search string: {var_id}"
        raise ClanError(msg)
    if len(results) > 1:
        error = (
            f"Found multiple vars for {var_id}:\n  - "
            + "\n  - ".join([str(var) for var in results])
            + "\nBe more specific."
        )
        raise ClanError(error)
    # we have exactly one result at this point
    var = results[0]
    if var_id == var.id:
        return var
    msg = f"Did you mean: {var.id}"
    raise ClanError(msg)


def get_command(machine: str, var_id: str, flake: FlakeId) -> None:
    _machine = Machine(name=machine, flake=flake)
    var = get_var(_machine, var_id)
    if not var.exists:
        msg = f"Var {var.id} has not been generated yet"
        raise ClanError(msg)
    if sys.stdout.isatty():
        sys.stdout.buffer.write(var.value)
    else:
        print(var.printable_value)


def _get_command(
    args: argparse.Namespace,
) -> None:
    get_command(
        machine=args.machine,
        var_id=args.var_id,
        flake=args.flake,
    )


def register_get_parser(parser: argparse.ArgumentParser) -> None:
    machines_arg = parser.add_argument(
        "machine",
        help="The machine to print vars for",
    )
    add_dynamic_completer(machines_arg, complete_machines)

    parser.add_argument(
        "var_id",
        help="The var id to get the value for. Example: ssh-keys/pubkey",
    )

    parser.set_defaults(func=_get_command)
