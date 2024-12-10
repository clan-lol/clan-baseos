import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

from clan_cli.cmd import RunOpts, run
from clan_cli.completions import (
    add_dynamic_completer,
    complete_machines,
    complete_services_for_machine,
)
from clan_cli.errors import ClanError
from clan_cli.git import commit_files
from clan_cli.machines.inventory import get_all_machines, get_selected_machines
from clan_cli.nix import nix_shell
from clan_cli.vars._types import StoreBase

from .check import check_vars
from .graph import (
    minimal_closure,
    requested_closure,
)
from .prompt import Prompt, ask
from .var import Var

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from clan_cli.machines.machines import Machine


@dataclass
class Generator:
    name: str
    files: list[Var] = field(default_factory=list)
    share: bool = False
    validation: str | None = None
    final_script: str = ""
    prompts: list[Prompt] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    migrate_fact: str | None = None

    # TODO: remove this
    _machine: "Machine | None" = None

    def machine(self, machine: "Machine") -> None:
        self._machine = machine

    @cached_property
    def exists(self) -> bool:
        assert self._machine is not None
        return check_vars(self._machine, generator_name=self.name)

    @classmethod
    def from_json(cls: type["Generator"], data: dict[str, Any]) -> "Generator":
        return cls(
            name=data["name"],
            share=data["share"],
            final_script=data["finalScript"],
            files=[Var.from_json(data["name"], f) for f in data["files"].values()],
            validation=data["validationHash"],
            dependencies=data["dependencies"],
            migrate_fact=data["migrateFact"],
            prompts=[Prompt.from_json(p) for p in data["prompts"].values()],
        )


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
    machine: "Machine",
    generator: Generator,
    secret_vars_store: StoreBase,
    public_vars_store: StoreBase,
) -> dict[str, dict[str, bytes]]:
    decrypted_dependencies: dict[str, Any] = {}
    for generator_name in set(generator.dependencies):
        decrypted_dependencies[generator_name] = {}
        for dep_generator in machine.vars_generators:
            if generator_name == dep_generator.name:
                break
        else:
            msg = f"Could not find dependent generator {generator_name} in machine {machine.name}"
            raise ClanError(msg)
        dep_files = dep_generator.files
        for file in dep_files:
            if file.secret:
                decrypted_dependencies[generator_name][file.name] = (
                    secret_vars_store.get(dep_generator, file.name)
                )
            else:
                decrypted_dependencies[generator_name][file.name] = (
                    public_vars_store.get(dep_generator, file.name)
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
    machine: "Machine",
    generator: Generator,
    secret_vars_store: StoreBase,
    public_vars_store: StoreBase,
    prompt_values: dict[str, str],
) -> None:
    if not isinstance(machine.flake, Path):
        msg = f"flake is not a Path: {machine.flake}"
        msg += "fact/secret generation is only supported for local flakes"

    # build temporary file tree of dependencies
    decrypted_dependencies = decrypt_dependencies(
        machine,
        generator,
        secret_vars_store,
        public_vars_store,
    )

    def get_prompt_value(prompt_name: str) -> str:
        try:
            return prompt_values[prompt_name]
        except KeyError as e:
            msg = f"prompt value for '{prompt_name}' in generator {generator.name} not provided"
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
        if generator.prompts:
            tmpdir_prompts.mkdir()
            env["prompts"] = str(tmpdir_prompts)
            for prompt in generator.prompts:
                prompt_file = tmpdir_prompts / prompt.name
                value = get_prompt_value(prompt.name)
                prompt_file.write_text(value)

        if sys.platform == "linux":
            cmd = bubblewrap_cmd(generator.final_script, tmpdir)
        else:
            cmd = ["bash", "-c", generator.final_script]
        run(cmd, RunOpts(env=env))
        files_to_commit = []
        # store secrets
        files = generator.files
        public_changed = False
        secret_changed = False
        for file in files:
            secret_file = tmpdir_out / file.name
            if not secret_file.is_file():
                msg = f"did not generate a file for '{file.name}' when running the following command:\n"
                msg += generator.final_script
                raise ClanError(msg)
            if file.secret:
                file_path = secret_vars_store.set(
                    generator,
                    file,
                    secret_file.read_bytes(),
                )
                secret_changed = True
            else:
                file_path = public_vars_store.set(
                    generator,
                    file,
                    secret_file.read_bytes(),
                )
                public_changed = True
            if file_path:
                files_to_commit.append(file_path)
            if generator.validation is not None:
                if public_changed:
                    public_vars_store.set_validation(generator, generator.validation)
                if secret_changed:
                    secret_vars_store.set_validation(generator, generator.validation)
    commit_files(
        files_to_commit,
        machine.flake_dir,
        f"Update vars via generator {generator.name} for machine {machine.name}",
    )


def _ask_prompts(
    generator: Generator,
) -> dict[str, str]:
    prompt_values: dict[str, str] = {}
    for prompt in generator.prompts:
        var_id = f"{generator.name}/{prompt.name}"
        prompt_values[prompt.name] = ask(var_id, prompt.prompt_type)
    return prompt_values


def get_closure(
    machine: "Machine",
    generator_name: str | None,
    regenerate: bool,
) -> list[Generator]:
    from .graph import all_missing_closure, full_closure

    vars_generators = machine.vars_generators
    generators: dict[str, Generator] = {
        generator.name: generator for generator in vars_generators
    }

    # TODO: we should remove this
    for generator in vars_generators:
        generator.machine(machine)

    if generator_name is None:  # all generators selected
        if regenerate:
            return full_closure(generators)
        return all_missing_closure(generators)
    # specific generator selected
    if regenerate:
        return requested_closure([generator_name], generators)
    return minimal_closure([generator_name], generators)


def _migration_file_exists(
    machine: "Machine",
    generator: Generator,
    fact_name: str,
) -> bool:
    for file in generator.files:
        if file.name == fact_name:
            break
    else:
        msg = f"Could not find file {fact_name} in generator {generator.name}"
        raise ClanError(msg)

    is_secret = file.secret
    if is_secret:
        if machine.secret_facts_store.exists(generator.name, fact_name):
            return True
        log.debug(
            f"Cannot migrate fact {fact_name} for service {generator.name}, as it does not exist in the secret fact store"
        )
    if not is_secret:
        if machine.public_facts_store.exists(generator.name, fact_name):
            return True
        log.debug(
            f"Cannot migrate fact {fact_name} for service {generator.name}, as it does not exist in the public fact store"
        )
    return False


def _migrate_file(
    machine: "Machine",
    generator: Generator,
    var_name: str,
    service_name: str,
    fact_name: str,
) -> list[Path]:
    for file in generator.files:
        if file.name == var_name:
            break
    else:
        msg = f"Could not find file {fact_name} in generator {generator.name}"
        raise ClanError(msg)

    paths = []

    if file.secret:
        old_value = machine.secret_facts_store.get(service_name, fact_name)
        maybe_path = machine.secret_vars_store.set(
            generator, file, old_value, is_migration=True
        )
        if maybe_path:
            paths.append(maybe_path)
    else:
        old_value = machine.public_facts_store.get(service_name, fact_name)
        maybe_path = machine.public_vars_store.set(
            generator, file, old_value, is_migration=True
        )
        if maybe_path:
            paths.append(maybe_path)

    return paths


def _migrate_files(
    machine: "Machine",
    generator: Generator,
) -> None:
    not_found = []
    files_to_commit = []
    for file in generator.files:
        if _migration_file_exists(machine, generator, file.name):
            assert generator.migrate_fact is not None
            files_to_commit += _migrate_file(
                machine, generator, file.name, generator.migrate_fact, file.name
            )
        else:
            not_found.append(file.name)
    if len(not_found) > 0:
        msg = f"Could not migrate the following files for generator {generator.name}, as no fact or secret exists with the same name: {not_found}"
        raise ClanError(msg)
    commit_files(
        files_to_commit,
        machine.flake_dir,
        f"migrated facts to vars for generator {generator.name} for machine {machine.name}",
    )


def _check_can_migrate(
    machine: "Machine",
    generator: Generator,
) -> bool:
    service_name = generator.migrate_fact
    if not service_name:
        return False
    # ensure that none of the generated vars already exist in the store
    all_files_missing = True
    all_files_present = True
    for file in generator.files:
        if file.secret:
            if machine.secret_vars_store.exists(generator, file.name):
                all_files_missing = False
            else:
                all_files_present = False
        else:
            if machine.public_vars_store.exists(generator, file.name):
                all_files_missing = False
            else:
                all_files_present = False

    if not all_files_present and not all_files_missing:
        msg = f"Cannot migrate facts for generator {generator.name} as some files already exist in the store"
        raise ClanError(msg)
    if all_files_present:
        # all filles already migrated, no need to run migration again
        return False

    # ensure that all files can be migrated (exists in the corresponding fact store)
    return bool(
        all(
            _migration_file_exists(machine, generator, file.name)
            for file in generator.files
        )
    )


def generate_vars_for_machine(
    machine: "Machine",
    generator_name: str | None,
    regenerate: bool,
) -> bool:
    _generator = None
    if generator_name:
        for generator in machine.vars_generators:
            if generator.name == generator_name:
                _generator = generator
                break

    pub_healtcheck_msg = machine.public_vars_store.health_check(_generator)
    sec_healtcheck_msg = machine.secret_vars_store.health_check(_generator)

    if pub_healtcheck_msg or sec_healtcheck_msg:
        msg = f"Health check failed for machine {machine.name}:\n"
        if pub_healtcheck_msg:
            msg += f"Public vars store: {pub_healtcheck_msg}\n"
        if sec_healtcheck_msg:
            msg += f"Secret vars store: {sec_healtcheck_msg}"
        raise ClanError(msg)

    closure = get_closure(machine, generator_name, regenerate)
    if len(closure) == 0:
        return False
    for generator in closure:
        if _check_can_migrate(machine, generator):
            _migrate_files(machine, generator)
        else:
            execute_generator(
                machine=machine,
                generator=generator,
                secret_vars_store=machine.secret_vars_store,
                public_vars_store=machine.public_vars_store,
                prompt_values=_ask_prompts(generator),
            )
    # flush caches to make sure the new secrets are available in evaluation
    machine.flush_caches()
    return True


def generate_vars(
    machines: list["Machine"],
    generator_name: str | None = None,
    regenerate: bool = False,
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
            errors += [(machine, exc)]
        if len(errors) == 1:
            raise errors[0][1]
        if len(errors) > 1:
            msg = f"Failed to generate facts for {len(errors)} hosts:"
            for machine, error in errors:
                msg += f"\n{machine}: {error}"
            raise ClanError(msg) from errors[0][1]

    if not was_regenerated and len(machines) > 0:
        for machine in machines:
            machine.info("All vars are already up to date")

    return was_regenerated


def generate_command(args: argparse.Namespace) -> None:
    if args.flake is None:
        msg = "Could not find clan flake toplevel directory"
        raise ClanError(msg)
    if len(args.machines) == 0:
        machines = get_all_machines(args.flake, args.option)
    else:
        machines = get_selected_machines(args.flake, args.option, args.machines)
    generate_vars(machines, args.generator, args.regenerate)


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
        "--generator",
        "-g",
        type=str,
        help="execute only the specified generator. If unset, execute all generators",
        default=None,
    )
    add_dynamic_completer(service_parser, complete_services_for_machine)

    parser.add_argument(
        "--regenerate",
        "-r",
        action=argparse.BooleanOptionalAction,
        help="whether to regenerate facts for the specified machine",
        default=None,
    )

    parser.set_defaults(func=generate_command)
