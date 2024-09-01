# !/usr/bin/env python3
from abc import ABC, abstractmethod
from dataclasses import dataclass

from clan_cli.machines.machines import Machine


@dataclass
class Var:
    store: "StoreBase"
    generator: str
    name: str
    secret: bool
    shared: bool
    deployed: bool

    def __str__(self) -> str:
        if self.secret:
            return f"{self.generator}/{self.name}: ********"
        return f"{self.generator}/{self.name}: {self.store.get(self.generator, self.name, self.shared).decode()}"


class StoreBase(ABC):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine

    @abstractmethod
    def exists(self, service: str, name: str, shared: bool = False) -> bool:
        pass

    # get a single fact
    @abstractmethod
    def get(self, service: str, name: str, shared: bool = False) -> bytes:
        pass

    def get_all(self) -> list[Var]:
        all_vars = []
        for gen_name, generator in self.machine.vars_generators.items():
            for f_name, file in generator["files"].items():
                all_vars.append(
                    Var(
                        store=self,
                        generator=gen_name,
                        name=f_name,
                        secret=file["secret"],
                        shared=generator["share"],
                        deployed=file["deploy"],
                    )
                )
        return all_vars
