# !/usr/bin/env python3
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

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

    @property
    @abstractmethod
    def store_name(self) -> str:
        pass

    # get a single fact
    @abstractmethod
    def get(self, generator_name: str, name: str, shared: bool = False) -> bytes:
        pass

    @abstractmethod
    def _set(
        self,
        generator_name: str,
        name: str,
        value: bytes,
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        """
        override this method to implement the actual creation of the file
        """

    @property
    @abstractmethod
    def is_secret_store(self) -> bool:
        pass

    def directory(
        self, generator_name: str, var_name: str, shared: bool = False
    ) -> Path:
        if shared:
            base_path = self.machine.flake_dir / "vars" / "shared"
        else:
            base_path = (
                self.machine.flake_dir / "vars" / "per-machine" / self.machine.name
            )
        return base_path / generator_name / var_name

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        directory = self.directory(generator_name, name, shared)
        if not (directory / "meta.json").exists():
            return False
        with (directory / "meta.json").open() as f:
            meta = json.load(f)
        # check if is secret, as secret and public store names could collide (eg. 'vm')
        if meta.get("secret") != self.is_secret_store:
            return False
        return meta.get("store") == self.store_name

    def set(
        self,
        generator_name: str,
        var_name: str,
        value: bytes,
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        directory = self.directory(generator_name, var_name, shared)
        # delete directory
        if directory.exists():
            for f in directory.glob("*"):
                f.unlink()
        # re-create directory
        directory.mkdir(parents=True, exist_ok=True)
        new_file = self._set(generator_name, var_name, value, shared, deployed)
        meta = {
            "deployed": deployed,
            "secret": self.is_secret_store,
            "store": self.store_name,
        }
        with (directory / "meta.json").open("w") as file:
            json.dump(meta, file, indent=2)
        return new_file

    def get_all(self) -> list[Var]:
        all_vars = []
        for gen_name, generator in self.machine.vars_generators.items():
            for f_name, file in generator["files"].items():
                # only handle vars compatible to this store
                if self.is_secret_store != file["secret"]:
                    continue
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
