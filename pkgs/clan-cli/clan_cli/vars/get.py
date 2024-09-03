import argparse
import logging
import sys

from clan_cli.clan_uri import FlakeId
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine

from ._types import Var
from .list import all_vars

log = logging.getLogger(__name__)


def get_var(machine: Machine, var_id: str) -> Var | None:
    vars_ = all_vars(machine)
    results = []
    for var in vars_:
        if var_id in var.id:
            results.append(var)
    if len(results) == 0:
        return None
    if len(results) > 1:
        error = (
            f"Found multiple vars for {var_id}:\n  - "
            + "\n  - ".join([str(var) for var in results])
            + "\nBe more specific."
        )
        raise ClanError(error)
    # we have exactly one result at this point
    result = results[0]
    if var_id == result.id:
        return result
    msg = f"Did you mean: {result.id}"
    raise ClanError(msg)


def get_command(
    machine: str, var_id: str, flake: FlakeId, quiet: bool, **kwargs: dict
) -> None:
    _machine = Machine(name=machine, flake=flake)
    var = get_var(_machine, var_id)
    if var is None:
        msg = f"No var found for search string: {var_id}"
        raise ClanError(msg)
    if not var.exists:
        msg = f"Var {var.id} has not been generated yet"
        raise ClanError(msg)
    if quiet:
        sys.stdout.buffer.write(var.value)
    else:
        print(f"{var.id}: {var.printable_value}")


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

    parser.add_argument(
        "--quiet",
        "-q",
        help="Only print the value of the var",
        action="store_true",
    )
    parser.set_defaults(func=lambda args: get_command(**vars(args)))
