import argparse
import importlib
import logging

from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine
from clan_cli.vars.public_modules import FactStoreBase
from clan_cli.vars.secret_modules import SecretStoreBase

log = logging.getLogger(__name__)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .generate import Var


class VarStatus:
    def __init__(
        self,
        missing_secret_vars: list["Var"],
        missing_public_vars: list["Var"],
        unfixed_secret_vars: list["Var"],
        invalid_generators: list[str],
    ) -> None:
        self.missing_secret_vars = missing_secret_vars
        self.missing_public_vars = missing_public_vars
        self.unfixed_secret_vars = unfixed_secret_vars
        self.invalid_generators = invalid_generators


def vars_status(machine: Machine, generator_name: None | str = None) -> VarStatus:
    secret_vars_module = importlib.import_module(machine.secret_vars_module)
    secret_vars_store: SecretStoreBase = secret_vars_module.SecretStore(machine=machine)
    public_vars_module = importlib.import_module(machine.public_vars_module)
    public_vars_store: FactStoreBase = public_vars_module.FactStore(machine=machine)

    missing_secret_vars = []
    missing_public_vars = []
    # signals if a var needs to be updated (eg. needs re-encryption due to new users added)
    unfixed_secret_vars = []
    invalid_generators = []
    generators = machine.vars_generators
    if generator_name:
        for generator in generators:
            if generator_name == generator.name:
                generators = [generator]
                break
        else:
            err_msg = (
                f"Generator '{generator_name}' not found in machine {machine.name}"
            )
            raise ClanError(err_msg)

    for generator in generators:
        generator.machine(machine)
        for file in generator.files:
            file.store(secret_vars_store if file.secret else public_vars_store)
            file.generator(generator)

            if file.secret:
                if not secret_vars_store.exists(generator, file.name):
                    log.info(
                        f"Secret var '{file.name}' for service '{generator.name}' in machine {machine.name} is missing."
                    )
                    missing_secret_vars.append(file)
                else:
                    msg = secret_vars_store.health_check(
                        generator=generator,
                        file_name=file.name,
                    )
                    if msg:
                        log.info(
                            f"Secret var '{file.name}' for service '{generator.name}' in machine {machine.name} needs update: {msg}"
                        )
                        unfixed_secret_vars.append(file)

            elif not public_vars_store.exists(generator, file.name):
                log.info(
                    f"Public var '{file.name}' for service '{generator.name}' in machine {machine.name} is missing."
                )
                missing_public_vars.append(file)
        # check if invalidation hash is up to date
        if not (
            secret_vars_store.hash_is_valid(generator)
            and public_vars_store.hash_is_valid(generator)
        ):
            invalid_generators.append(generator.name)
            log.info(
                f"Generator '{generator.name}' in machine {machine.name} has outdated invalidation hash."
            )
    log.debug(f"missing_secret_vars: {missing_secret_vars}")
    log.debug(f"missing_public_vars: {missing_public_vars}")
    log.debug(f"unfixed_secret_vars: {unfixed_secret_vars}")
    log.debug(f"invalid_generators: {invalid_generators}")
    return VarStatus(
        missing_secret_vars,
        missing_public_vars,
        unfixed_secret_vars,
        invalid_generators,
    )


def check_vars(machine: Machine, generator_name: None | str = None) -> bool:
    status = vars_status(machine, generator_name=generator_name)
    return not (
        status.missing_secret_vars
        or status.missing_public_vars
        or status.unfixed_secret_vars
        or status.invalid_generators
    )


def check_command(args: argparse.Namespace) -> None:
    machine = Machine(
        name=args.machine,
        flake=args.flake,
    )
    ok = check_vars(machine, generator_name=args.generator)
    if not ok:
        raise SystemExit(1)


def register_check_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        help="The machine to check secrets for",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.add_argument(
        "--generator",
        "-g",
        help="the generator to check",
    )
    parser.set_defaults(func=check_command)
