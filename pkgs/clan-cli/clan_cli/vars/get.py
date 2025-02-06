import argparse
import logging
import sys

from clan_cli.api import API
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.errors import ClanError
from clan_cli.flake import Flake

from .generate import Var
from .list import get_vars

log = logging.getLogger(__name__)


@API.register
def get_var(base_dir: str, machine_name: str, var_id: str) -> Var:
    vars_ = get_vars(base_dir=base_dir, machine_name=machine_name)
    results = []
    for var in vars_:
        if var.id == var_id:
            # exact match
            results = [var]
            break
        if var.id.startswith(var_id):
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


def get_command(machine_name: str, var_id: str, flake: Flake) -> None:
    var = get_var(str(flake.path), machine_name, var_id)
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
        machine_name=args.machine,
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
