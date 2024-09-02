import argparse
import importlib
import logging
import os
import sys
from getpass import getpass
from graphlib import TopologicalSorter
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

from .check import check_vars
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
    shared: bool,
) -> dict[str, dict[str, bytes]]:
    generator = machine.vars_generators[generator_name]
    dependencies = set(generator["dependencies"])
    decrypted_dependencies: dict[str, Any] = {}
    for dep_generator in dependencies:
        decrypted_dependencies[dep_generator] = {}
        dep_files = machine.vars_generators[dep_generator]["files"]
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
    regenerate: bool,
    secret_vars_store: SecretStoreBase,
    public_vars_store: FactStoreBase,
) -> bool:
    # check if all secrets exist and generate them if at least one is missing
    needs_regeneration = not check_vars(machine, generator_name=generator_name)
    log.debug(f"{generator_name} needs_regeneration: {needs_regeneration}")
    if not (needs_regeneration or regenerate):
        return False
    if not isinstance(machine.flake, Path):
        msg = f"flake is not a Path: {machine.flake}"
        msg += "fact/secret generation is only supported for local flakes"

    generator = machine.vars_generators[generator_name]["finalScript"]
    is_shared = machine.vars_generators[generator_name]["share"]

    # build temporary file tree of dependencies
    decrypted_dependencies = decrypt_dependencies(
        machine, generator_name, secret_vars_store, public_vars_store, shared=is_shared
    )
    env = os.environ.copy()
    with TemporaryDirectory() as tmp:
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
            for prompt_name, prompt in machine.vars_generators[generator_name][
                "prompts"
            ].items():
                prompt_file = tmpdir_prompts / prompt_name
                value = prompt_func(prompt["description"], prompt["type"])
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
            groups = machine.deployment["sops"]["defaultGroups"]

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
                    groups,
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
        f"Update facts/secrets for service {generator_name} in machine {machine.name}",
    )
    return True


def prompt_func(description: str, input_type: str) -> str:
    if input_type == "line":
        result = input(f"Enter the value for {description}: ")
    elif input_type == "multiline":
        print(f"Enter the value for {description} (Finish with Ctrl-D): ")
        result = sys.stdin.read()
    elif input_type == "hidden":
        result = getpass(f"Enter the value for {description} (hidden): ")
    else:
        raise ClanError(f"Unknown input type: {input_type} for prompt {description}")
    log.info("Input received. Processing...")
    return result


def _get_subgraph(graph: dict[str, set], vertex: str) -> dict[str, set]:
    visited = set()
    queue = [vertex]
    while queue:
        vertex = queue.pop(0)
        if vertex not in visited:
            visited.add(vertex)
            queue.extend(graph[vertex] - visited)
    return {k: v for k, v in graph.items() if k in visited}


def _generate_vars_for_machine(
    machine: Machine,
    generator_name: str | None,
    regenerate: bool,
) -> bool:
    secret_vars_module = importlib.import_module(machine.secret_vars_module)
    secret_vars_store = secret_vars_module.SecretStore(machine=machine)

    public_vars_module = importlib.import_module(machine.public_vars_module)
    public_vars_store = public_vars_module.FactStore(machine=machine)

    machine_updated = False

    if generator_name and generator_name not in machine.vars_generators:
        generators = list(machine.vars_generators.keys())
        raise ClanError(
            f"Could not find generator with name: {generator_name}. The following generators are available: {generators}"
        )

    graph = {
        gen_name: set(generator["dependencies"])
        for gen_name, generator in machine.vars_generators.items()
    }

    # extract sub-graph if specific generator selected
    if generator_name:
        graph = _get_subgraph(graph, generator_name)

    # check if all dependencies actually exist
    for gen_name, dependencies in graph.items():
        for dep in dependencies:
            if dep not in graph:
                raise ClanError(
                    f"Generator {gen_name} has a dependency on {dep}, which does not exist"
                )

    # process generators in topological order
    sorter = TopologicalSorter(graph)
    for generator_name in sorter.static_order():
        assert generator_name is not None
        machine_updated |= execute_generator(
            machine=machine,
            generator_name=generator_name,
            regenerate=regenerate,
            secret_vars_store=secret_vars_store,
            public_vars_store=public_vars_store,
        )
    if machine_updated:
        # flush caches to make sure the new secrets are available in evaluation
        machine.flush_caches()
    return machine_updated


def generate_vars(
    machines: list[Machine],
    generator_name: str | None,
    regenerate: bool,
) -> bool:
    was_regenerated = False
    for machine in machines:
        errors = []
        try:
            was_regenerated |= _generate_vars_for_machine(
                machine, generator_name, regenerate
            )
        except Exception as exc:
            log.error(f"Failed to generate facts for {machine.name}: {exc}")
            errors += [exc]
        if len(errors) > 0:
            raise ClanError(
                f"Failed to generate facts for {len(errors)} hosts. Check the logs above"
            ) from errors[0]

    if not was_regenerated:
        print("All secrets and facts are already up to date")
    return was_regenerated


def generate_command(args: argparse.Namespace) -> None:
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
        type=bool,
        action=argparse.BooleanOptionalAction,
        help="whether to regenerate facts for the specified machine",
        default=None,
    )
    parser.set_defaults(func=generate_command)
