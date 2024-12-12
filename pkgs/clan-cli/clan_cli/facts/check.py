import argparse
import importlib
import logging

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

log = logging.getLogger(__name__)


def check_secrets(machine: Machine, service: None | str = None) -> bool:
    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    secret_facts_store = secret_facts_module.SecretStore(machine=machine)
    public_facts_module = importlib.import_module(machine.public_facts_module)
    public_facts_store = public_facts_module.FactStore(machine=machine)

    missing_secret_facts = []
    missing_public_facts = []
    services = [service] if service else list(machine.facts_data.keys())
    for service in services:
        for secret_fact in machine.facts_data[service]["secret"]:
            if isinstance(secret_fact, str):
                secret_name = secret_fact
            else:
                secret_name = secret_fact["name"]
            if not secret_facts_store.exists(service, secret_name):
                machine.info(
                    f"Secret fact '{secret_fact}' for service '{service}' is missing."
                )
                missing_secret_facts.append((service, secret_name))

        for public_fact in machine.facts_data[service]["public"]:
            if not public_facts_store.exists(service, public_fact):
                machine.info(
                    f"Public fact '{public_fact}' for service '{service}' is missing."
                )
                missing_public_facts.append((service, public_fact))

    machine.debug(f"missing_secret_facts: {missing_secret_facts}")
    machine.debug(f"missing_public_facts: {missing_public_facts}")
    return not (missing_secret_facts or missing_public_facts)


def check_command(args: argparse.Namespace) -> None:
    machine = Machine(
        name=args.machine,
        flake=args.flake,
    )
    check_secrets(machine, service=args.service)


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
