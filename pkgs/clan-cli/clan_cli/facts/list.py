import argparse
import importlib
import json
import logging

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

log = logging.getLogger(__name__)


# TODO get also secret facts
def get_all_facts(machine: Machine) -> dict:
    public_facts_module = importlib.import_module(machine.public_facts_module)
    public_facts_store = public_facts_module.FactStore(machine=machine)

    # for service in machine.secrets_data:
    #     facts[service] = {}
    #     for fact in machine.secrets_data[service]["facts"]:
    #         fact_content = fact_store.get(service, fact)
    #         if fact_content:
    #             facts[service][fact] = fact_content.decode()
    #         else:
    #             log.error(f"Fact {fact} for service {service} is missing")
    return public_facts_store.get_all()


def get_command(args: argparse.Namespace) -> None:
    machine = Machine(name=args.machine, flake=args.flake)

    # the raw_facts are bytestrings making them not json serializable
    raw_facts = get_all_facts(machine)
    facts = dict()
    for key in raw_facts["TODO"]:
        facts[key] = raw_facts["TODO"][key].decode("utf8")

    print(json.dumps(facts, indent=4))


def register_list_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to print facts for",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.set_defaults(func=get_command)
