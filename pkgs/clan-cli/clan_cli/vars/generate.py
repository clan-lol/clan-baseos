import argparse
import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from clan_cli.cmd import run
from clan_cli.completions import (
    add_dynamic_completer,
    complete_machines,
    complete_services_for_machine,
)
from clan_cli.errors import ClanError
from clan_cli.git import commit_files
from clan_cli.machines.inventory import get_all_machines, get_selected_machines
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

from .graph import (
    minimal_closure,
    requested_closure,
)
from .prompt import ask
from .public_modules import FactStoreBase
from .secret_modules import SecretStoreBase

log = logging.getLogger(__name__)


def bubblewrap_cmd(generator: str, tmpdir: Path) -> list[str]:
    # fmt: off
    return nix_shell(
        [
            "nixpkgs#bash",
            "nixpkgs#bubblewrap",
        ],
        [
            "bwrap",
            "--ro-bind", "/nix/store", "/nix/store",
            "--tmpfs",  "/usr/lib/systemd",
            "--dev", "/dev",
            "--bind", str(tmpdir), str(tmpdir),
            "--unshare-all",
            "--unshare-user",
            "--uid", "1000",
            "--",
            "bash", "-c", generator
        ],
    )
    # fmt: on


# TODO: implement caching to not decrypt the same secret multiple times
def decrypt_dependencies(
    machine: Machine,
    generator_name: str,
    secret_vars_store: SecretStoreBase,
    public_vars_store: FactStoreBase,
) -> dict[str, dict[str, bytes]]:
    generator = machine.vars_generators[generator_name]
    dependencies = set(generator["dependencies"])
    decrypted_dependencies: dict[str, Any] = {}
    for dep_generator in dependencies:
        decrypted_dependencies[dep_generator] = {}
        dep_files = machine.vars_generators[dep_generator]["files"]
        shared = machine.vars_generators[dep_generator]["share"]
        for file_name, file in dep_files.items():
            if file["secret"]:
                decrypted_dependencies[dep_generator][file_name] = (
                    secret_vars_store.get(dep_generator, file_name, shared=shared)
                )
            else:
                decrypted_dependencies[dep_generator][file_name] = (
                    public_vars_store.get(dep_generator, file_name, shared=shared)
                )
    return decrypted_dependencies


# decrypt dependencies and return temporary file tree
def dependencies_as_dir(
    decrypted_dependencies: dict[str, dict[str, bytes]],
    tmpdir: Path,
) -> None:
    for dep_generator, files in decrypted_dependencies.items():
        dep_generator_dir = tmpdir / dep_generator
        dep_generator_dir.mkdir()
        dep_generator_dir.chmod(0o700)
        for file_name, file in files.items():
            file_path = dep_generator_dir / file_name
            file_path.touch()
            file_path.chmod(0o600)
            file_path.write_bytes(file)


def execute_generator(
    machine: Machine,
    generator_name: str,
    secret_vars_store: SecretStoreBase,
    public_vars_store: FactStoreBase,
    prompt_values: dict[str, str],
) -> None:
    if not isinstance(machine.flake, Path):
        msg = f"flake is not a Path: {machine.flake}"
        msg += "fact/secret generation is only supported for local flakes"

    generator = machine.vars_generators[generator_name]["finalScript"]
    is_shared = machine.vars_generators[generator_name]["share"]

    # build temporary file tree of dependencies
    decrypted_dependencies = decrypt_dependencies(
        machine,
        generator_name,
        secret_vars_store,
        public_vars_store,
    )

    def get_prompt_value(prompt_name: str) -> str:
        try:
            return prompt_values[prompt_name]
        except KeyError as e:
            msg = f"prompt value for '{prompt_name}' in generator {generator_name} not provided"
            raise ClanError(msg) from e

    env = os.environ.copy()
    with TemporaryDirectory(prefix="vars-") as tmp:
        tmpdir = Path(tmp)
        tmpdir_in = tmpdir / "in"
        tmpdir_prompts = tmpdir / "prompts"
        tmpdir_out = tmpdir / "out"
        tmpdir_in.mkdir()
        tmpdir_out.mkdir()
        env["in"] = str(tmpdir_in)
        env["out"] = str(tmpdir_out)
        # populate dependency inputs
        dependencies_as_dir(decrypted_dependencies, tmpdir_in)
        # populate prompted values
        # TODO: make prompts rest API friendly
        if machine.vars_generators[generator_name]["prompts"]:
            tmpdir_prompts.mkdir()
            env["prompts"] = str(tmpdir_prompts)
            for prompt_name in machine.vars_generators[generator_name]["prompts"]:
                prompt_file = tmpdir_prompts / prompt_name
                value = get_prompt_value(prompt_name)
                prompt_file.write_text(value)

        if sys.platform == "linux":
            cmd = bubblewrap_cmd(generator, tmpdir)
        else:
            cmd = ["bash", "-c", generator]
        run(
            cmd,
            env=env,
        )
        files_to_commit = []
        # store secrets
        files = machine.vars_generators[generator_name]["files"]
        for file_name, file in files.items():
            is_deployed = file["deploy"]

            secret_file = tmpdir_out / file_name
            if not secret_file.is_file():
                msg = f"did not generate a file for '{file_name}' when running the following command:\n"
                msg += generator
                raise ClanError(msg)
            if file["secret"]:
                file_path = secret_vars_store.set(
                    generator_name,
                    file_name,
                    secret_file.read_bytes(),
                    shared=is_shared,
                    deployed=is_deployed,
                )
            else:
                file_path = public_vars_store.set(
                    generator_name,
                    file_name,
                    secret_file.read_bytes(),
                    shared=is_shared,
                )
            if file_path:
                files_to_commit.append(file_path)
    commit_files(
        files_to_commit,
        machine.flake_dir,
        f"Update vars via generator {generator_name} for machine {machine.name}",
    )


def _ask_prompts(
    machine: Machine,
    generator_names: list[str],
) -> dict[str, dict[str, str]]:
    prompt_values: dict[str, dict[str, str]] = {}
    for generator in generator_names:
        prompts = machine.vars_generators[generator]["prompts"]
        for prompt_name, _prompt in prompts.items():
            if generator not in prompt_values:
                prompt_values[generator] = {}
            var_id = f"{generator}/{prompt_name}"
            prompt_values[generator][prompt_name] = ask(var_id, _prompt["type"])
    return prompt_values


def get_closure(
    machine: Machine,
    generator_name: str | None,
    regenerate: bool,
) -> list[str]:
    from .graph import Generator, all_missing_closure, full_closure

    vars_generators = machine.vars_generators
    generators: dict[str, Generator] = {
        name: Generator(name, generator["dependencies"], _machine=machine)
        for name, generator in vars_generators.items()
    }
    if generator_name is None:  # all generators selected
        if regenerate:
            return full_closure(generators)
        return all_missing_closure(generators)
    # specific generator selected
    if regenerate:
        return requested_closure([generator_name], generators)
    return minimal_closure([generator_name], generators)


def _migration_file_exists(
    machine: Machine,
    service_name: str,
    fact_name: str,
) -> bool:
    is_secret = machine.vars_generators[service_name]["files"][fact_name]["secret"]
    if is_secret:
        if machine.secret_facts_store.exists(service_name, fact_name):
            return True
        log.debug(
            f"Cannot migrate fact {fact_name} for service {service_name}, as it does not exist in the secret fact store"
        )
    if not is_secret:
        if machine.public_facts_store.exists(service_name, fact_name):
            return True
        log.debug(
            f"Cannot migrate fact {fact_name} for service {service_name}, as it does not exist in the public fact store"
        )
    return False


def _migrate_file(
    machine: Machine,
    generator_name: str,
    var_name: str,
    service_name: str,
    fact_name: str,
) -> None:
    is_secret = machine.vars_generators[generator_name]["files"][var_name]["secret"]
    if is_secret:
        old_value = machine.secret_facts_store.get(service_name, fact_name)
    else:
        old_value = machine.public_facts_store.get(service_name, fact_name)
    is_shared = machine.vars_generators[generator_name]["share"]
    is_deployed = machine.vars_generators[generator_name]["files"][var_name]["deploy"]
    machine.public_vars_store.set(
        generator_name, var_name, old_value, shared=is_shared, deployed=is_deployed
    )


def _migrate_files(
    machine: Machine,
    generator_name: str,
) -> None:
    service_name = machine.vars_generators[generator_name]["migrateFact"]
    not_found = []
    for var_name, _file in machine.vars_generators[generator_name]["files"].items():
        if _migration_file_exists(machine, generator_name, var_name):
            _migrate_file(machine, generator_name, var_name, service_name, var_name)
        else:
            not_found.append(var_name)
    if len(not_found) > 0:
        msg = f"Could not migrate the following files for generator {generator_name}, as no fact or secret exists with the same name: {not_found}"
        raise ClanError(msg)


def _check_can_migrate(
    machine: Machine,
    generator_name: str,
) -> bool:
    vars_generator = machine.vars_generators[generator_name]
    if "migrateFact" not in vars_generator:
        return False
    service_name = vars_generator["migrateFact"]
    if not service_name:
        return False
    # ensure that none of the generated vars already exist in the store
    for fname, file in vars_generator["files"].items():
        if file["secret"]:
            if machine.secret_vars_store.exists(
                generator_name, fname, vars_generator["share"]
            ):
                return False
        else:
            if machine.public_vars_store.exists(
                generator_name, fname, vars_generator["share"]
            ):
                return False
    # ensure that the service to migrate from actually exists
    if service_name not in machine.facts_data:
        log.debug(
            f"Could not migrate facts for generator {generator_name}, as the service {service_name} does not exist"
        )
        return False
    # ensure that all files can be migrated (exists in the corresponding fact store)
    return bool(
        all(
            _migration_file_exists(machine, generator_name, fname)
            for fname in vars_generator["files"]
        )
    )


def generate_vars_for_machine(
    machine: Machine,
    generator_name: str | None,
    regenerate: bool,
) -> bool:
    closure = get_closure(machine, generator_name, regenerate)
    if len(closure) == 0:
        return False
    prompt_values = _ask_prompts(machine, closure)
    for gen_name in closure:
        if _check_can_migrate(machine, gen_name):
            _migrate_files(machine, gen_name)
        else:
            execute_generator(
                machine,
                gen_name,
                machine.secret_vars_store,
                machine.public_vars_store,
                prompt_values.get(gen_name, {}),
            )
    # flush caches to make sure the new secrets are available in evaluation
    machine.flush_caches()
    return True


def generate_vars(
    machines: list[Machine],
    generator_name: str | None,
    regenerate: bool,
) -> bool:
    was_regenerated = False
    for machine in machines:
        errors = []
        try:
            was_regenerated |= generate_vars_for_machine(
                machine, generator_name, regenerate
            )
            machine.flush_caches()
        except Exception as exc:
            log.exception(f"Failed to generate facts for {machine.name}")
            errors += [exc]
        if len(errors) > 0:
            msg = f"Failed to generate facts for {len(errors)} hosts. Check the logs above"
            raise ClanError(msg) from errors[0]

    if not was_regenerated:
        print("All secrets and facts are already up to date")
    return was_regenerated


def generate_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    if len(args.machines) == 0:
        machines = get_all_machines(args.flake, args.option)
    else:
        machines = get_selected_machines(args.flake, args.option, args.machines)
    generate_vars(machines, args.service, args.regenerate)


def register_generate_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machines",
        type=str,
        help="machine to generate facts for. if empty, generate facts for all machines",
        nargs="*",
        default=[],
    )
    add_dynamic_completer(machines_parser, complete_machines)

    service_parser = parser.add_argument(
        "--service",
        type=str,
        help="service to generate facts for, if empty, generate facts for every service",
        default=None,
    )
    add_dynamic_completer(service_parser, complete_services_for_machine)

    parser.add_argument(
        "--regenerate",
        action=argparse.BooleanOptionalAction,
        help="whether to regenerate facts for the specified machine",
        default=None,
    )
    parser.set_defaults(func=generate_command)
