import argparse
import logging
import os
import sys
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
from .prompt import prompt
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
    prompt_values: dict[str, str] | None = None,
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

    def get_prompt_value(prompt_name: str) -> str:
        if prompt_values:
            try:
                return prompt_values[prompt_name]
            except KeyError as e:
                msg = f"prompt value for '{prompt_name}' in generator {generator_name} not provided"
                raise ClanError(msg) from e
        description = machine.vars_generators[generator_name]["prompts"][prompt_name][
            "description"
        ]
        _type = machine.vars_generators[generator_name]["prompts"][prompt_name]["type"]
        return prompt(description, _type)

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
        f"Update facts/secrets for service {generator_name} in machine {machine.name}",
    )
    return True


def _get_subgraph(graph: dict[str, set], vertices: list[str]) -> dict[str, set]:
    visited = set()
    queue = vertices
    while queue:
        vertex = queue.pop(0)
        if vertex not in visited:
            visited.add(vertex)
            queue.extend(graph[vertex] - visited)
    return {k: v for k, v in graph.items() if k in visited}


def _dependency_graph(
    machine: Machine, entry_nodes: None | list[str] = None
) -> dict[str, set]:
    graph = {
        gen_name: set(generator["dependencies"])
        for gen_name, generator in machine.vars_generators.items()
    }
    if entry_nodes:
        return _get_subgraph(graph, entry_nodes)
    return graph


def _reverse_dependency_graph(
    machine: Machine, entry_nodes: None | list[str] = None
) -> dict[str, set]:
    graph = _dependency_graph(machine)
    reverse_graph: dict[str, set] = {gen_name: set() for gen_name in graph}
    for gen_name, dependencies in graph.items():
        for dep in dependencies:
            reverse_graph[dep].add(gen_name)
    if entry_nodes:
        return _get_subgraph(reverse_graph, entry_nodes)
    return reverse_graph


def _required_generators(
    machine: Machine,
    desired_generators: list[str],
) -> list[str]:
    """
    Receives list fo desired generators to update and returns list of required generators to update.

    This is needed because some generators might depend on others, so we need to update them first.
    The returned list is sorted topologically.
    """

    dependency_graph = _dependency_graph(machine)
    # extract sub-graph if specific generators selected
    dependency_graph = _get_subgraph(dependency_graph, desired_generators)

    # check if all dependencies actually exist
    for gen_name, dependencies in dependency_graph.items():
        for dep in dependencies:
            if dep not in dependency_graph:
                msg = f"Generator {gen_name} has a dependency on {dep}, which does not exist"
                raise ClanError(msg)

    # ensure that all dependents are regenerated as well as their vars might depend on the current generator
    reverse_dependency_graph = _reverse_dependency_graph(machine, desired_generators)
    final_graph = _dependency_graph(
        machine, entry_nodes=list(reverse_dependency_graph.keys())
    )

    # process generators in topological order (dependencies first)
    sorter = TopologicalSorter(final_graph)
    return list(sorter.static_order())


def _generate_vars_for_machine(
    machine: Machine,
    generator_name: str | None,
    regenerate: bool,
) -> bool:
    return _generate_vars_for_machine_multi(
        machine, [generator_name] if generator_name else [], regenerate
    )


def _generate_vars_for_machine_multi(
    machine: Machine,
    generator_names: list[str],
    regenerate: bool,
) -> bool:
    machine_updated = False

    generators_to_update = _required_generators(machine, generator_names)
    for generator_name in generators_to_update:
        assert generator_name is not None
        machine_updated |= execute_generator(
            machine=machine,
            generator_name=generator_name,
            regenerate=regenerate,
            secret_vars_store=machine.secret_vars_store,
            public_vars_store=machine.public_vars_store,
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
            log.exception(f"Failed to generate facts for {machine.name}")
            errors += [exc]
        if len(errors) > 0:
            msg = f"Failed to generate facts for {len(errors)} hosts. Check the logs above"
            raise ClanError(msg) from errors[0]

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
