import argparse
import importlib
import logging

from clan_cli.api import API
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.errors import ClanError
from clan_cli.flake import Flake
from clan_cli.machines.machines import Machine
from clan_cli.vars._types import StoreBase

from ._types import GeneratorUpdate
from .generate import Generator, Prompt, Var, execute_generator

log = logging.getLogger(__name__)


def public_store(machine: Machine) -> StoreBase:
    public_vars_module = importlib.import_module(machine.public_vars_module)
    return public_vars_module.FactStore(machine=machine)


def secret_store(machine: Machine) -> StoreBase:
    secret_vars_module = importlib.import_module(machine.secret_vars_module)
    return secret_vars_module.SecretStore(machine=machine)


@API.register
def get_vars(base_dir: str, machine_name: str) -> list[Var]:
    machine = Machine(name=machine_name, flake=Flake(base_dir))
    pub_store = public_store(machine)
    sec_store = secret_store(machine)
    all_vars = []
    for generator in machine.vars_generators:
        for var in generator.files:
            if var.secret:
                var.store(sec_store)
            else:
                var.store(pub_store)
            var.generator(generator)
            all_vars.append(var)
    return all_vars


def _get_previous_value(
    machine: Machine,
    generator: Generator,
    prompt: Prompt,
) -> str | None:
    if not prompt.persist:
        return None

    pub_store = public_store(machine)
    if pub_store.exists(generator, prompt.name):
        return pub_store.get(generator, prompt.name).decode()
    sec_store = secret_store(machine)
    if sec_store.exists(generator, prompt.name):
        return sec_store.get(generator, prompt.name).decode()
    return None


@API.register
def get_generators(base_dir: str, machine_name: str) -> list[Generator]:
    machine = Machine(name=machine_name, flake=Flake(base_dir))
    generators: list[Generator] = machine.vars_generators
    for generator in generators:
        for prompt in generator.prompts:
            prompt.previous_value = _get_previous_value(machine, generator, prompt)
    return generators


# TODO: Ensure generator dependencies are met (executed in correct order etc.)
# TODO: for missing prompts, default to existing values
# TODO: raise error if mandatory prompt not provided
@API.register
def set_prompts(
    base_dir: str, machine_name: str, updates: list[GeneratorUpdate]
) -> None:
    machine = Machine(name=machine_name, flake=Flake(base_dir))
    for update in updates:
        for generator in machine.vars_generators:
            if generator.name == update.generator:
                break
        else:
            msg = f"Generator '{update.generator}' not found in machine {machine.name}"
            raise ClanError(msg)
        execute_generator(
            machine,
            generator,
            secret_vars_store=secret_store(machine),
            public_vars_store=public_store(machine),
            prompt_values=update.prompt_values,
        )


def stringify_vars(_vars: list[Var]) -> str:
    return "\n".join([str(var) for var in _vars])


def stringify_all_vars(machine: Machine) -> str:
    return stringify_vars(get_vars(str(machine.flake), machine.name))


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
