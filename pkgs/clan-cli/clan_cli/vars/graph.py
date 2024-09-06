from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from graphlib import TopologicalSorter

from clan_cli.machines.machines import Machine

from .check import check_vars


@dataclass
class Generator:
    name: str
    dependencies: list[str]
    _machine: Machine

    @cached_property
    def exists(self) -> bool:
        return check_vars(self._machine, generator_name=self.name)


def missing_dependency_closure(
    requested_generators: Iterable[str], generators: dict
) -> set[str]:
    closure = set(requested_generators)
    # extend the graph to include all dependencies which are not on disk
    dep_closure = set()
    queue = list(closure)
    while queue:
        gen_name = queue.pop(0)
        for dep in generators[gen_name].dependencies:
            if dep not in closure and not generators[dep].exists:
                dep_closure.add(dep)
                queue.append(dep)
    return dep_closure


def add_missing_dependencies(
    requested_generators: Iterable[str], generators: dict
) -> set[str]:
    closure = set(requested_generators)
    return missing_dependency_closure(closure, generators) | closure


def add_dependents(requested_generators: Iterable[str], generators: dict) -> set[str]:
    closure = set(requested_generators)
    # build reverse dependency graph (graph of dependents)
    dependents_graph: dict[str, set[str]] = {}
    for gen_name, gen in generators.items():
        for dep in gen.dependencies:
            if dep not in dependents_graph:
                dependents_graph[dep] = set()
            dependents_graph[dep].add(gen_name)
    # extend the graph to include all dependents of the current closure
    queue = list(closure)
    while queue:
        gen_name = queue.pop(0)
        for dep in dependents_graph.get(gen_name, []):
            if dep not in closure:
                closure.add(dep)
                queue.append(dep)
    return closure


def toposort_closure(_closure: Iterable[str], generators: dict) -> list[str]:
    closure = set(_closure)
    # return the topological sorted list of generators to execute
    final_dep_graph = {}
    for gen_name in sorted(closure):
        deps = set(generators[gen_name].dependencies) & closure
        final_dep_graph[gen_name] = deps
    sorter = TopologicalSorter(final_dep_graph)
    result = list(sorter.static_order())
    return result


# all generators in topological order
def full_closure(generators: dict) -> list[str]:
    return toposort_closure(generators.keys(), generators)


# just the missing generators including their dependents
def all_missing_closure(generators: dict) -> list[str]:
    # collect all generators that are missing from disk
    closure = {gen_name for gen_name, gen in generators.items() if not gen.exists}
    closure = add_dependents(closure, generators)
    return toposort_closure(closure, generators)


# only a selected list of generators including their missing dependencies and their dependents
def requested_closure(requested_generators: list[str], generators: dict) -> list[str]:
    closure = set(requested_generators)
    # extend the graph to include all dependencies which are not on disk
    closure = add_missing_dependencies(closure, generators)
    closure = add_dependents(closure, generators)
    return toposort_closure(closure, generators)


# just enough to ensure that the list of selected generators are in a consistent state.
# empty if nothing is missing.
def minimal_closure(requested_generators: list[str], generators: dict) -> list[str]:
    closure = set(requested_generators)
    final_closure = missing_dependency_closure(closure, generators)
    # add requested generators if not already exist
    for gen_name in closure:
        if not generators[gen_name].exists:
            final_closure.add(gen_name)
    return toposort_closure(final_closure, generators)
