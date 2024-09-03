import argparse
import importlib
import logging

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

log = logging.getLogger(__name__)


def check_vars(machine: Machine, generator_name: None | str = None) -> bool:
    secret_vars_module = importlib.import_module(machine.secret_vars_module)
    secret_vars_store = secret_vars_module.SecretStore(machine=machine)
    public_vars_module = importlib.import_module(machine.public_vars_module)
    public_vars_store = public_vars_module.FactStore(machine=machine)

    missing_secret_vars = []
    missing_public_vars = []
    if generator_name:
        generators = [generator_name]
    else:
        generators = list(machine.vars_generators.keys())
    for generator_name in generators:
        for name, file in machine.vars_generators[generator_name]["files"].items():
            if file["secret"] and not secret_vars_store.exists(generator_name, name):
                log.info(
                    f"Secret fact '{name}' for service '{generator_name}' in machine {machine.name} is missing."
                )
                missing_secret_vars.append((generator_name, name))
            if not file["secret"] and not public_vars_store.exists(
                generator_name, name
            ):
                log.info(
                    f"Public fact '{name}' for service '{generator_name}' in machine {machine.name} is missing."
                )
                missing_public_vars.append((generator_name, name))

    log.debug(f"missing_secret_vars: {missing_secret_vars}")
    log.debug(f"missing_public_vars: {missing_public_vars}")
    return not (missing_secret_vars or missing_public_vars)


def check_command(args: argparse.Namespace) -> None:
    machine = Machine(
        name=args.machine,
        flake=args.flake,
    )
    ok = check_vars(machine, generator_name=args.service)
    if not ok:
        raise SystemExit(1)


def register_check_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to check secrets for",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.add_argument(
        "--service",
        help="the service to check",
    )
    parser.set_defaults(func=check_command)
