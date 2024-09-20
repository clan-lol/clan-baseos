import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.machines import machines

log = logging.getLogger(__name__)


def string_repr(value: bytes) -> str:
    try:
        return value.decode()
    except UnicodeDecodeError:
        return "<binary blob>"


@dataclass
class Prompt:
    name: str
    description: str
    type: str
    has_file: bool
    generator: str
    previous_value: str | None = None


# TODO: add flag 'pending' generator needs to be executed
@dataclass
class Generator:
    name: str
    share: bool
    prompts: list[Prompt]


@dataclass
class GeneratorUpdate:
    generator: str
    prompt_values: dict[str, str]


@dataclass
class Var:
    _store: "StoreBase"
    generator: str
    name: str
    id: str
    secret: bool
    shared: bool
    deployed: bool

    @property
    def value(self) -> bytes:
        if not self._store.exists(self.generator, self.name, self.shared):
            msg = f"Var {self.id} has not been generated yet"
            raise ValueError(msg)
        # try decode the value or return <binary blob>
        return self._store.get(self.generator, self.name, self.shared)

    @property
    def printable_value(self) -> str:
        return string_repr(self.value)

    def set(self, value: bytes) -> None:
        self._store.set(self.generator, self.name, value, self.shared, self.deployed)

    @property
    def exists(self) -> bool:
        return self._store.exists(self.generator, self.name, self.shared)

    def __str__(self) -> str:
        if self._store.exists(self.generator, self.name, self.shared):
            if self.secret:
                return f"{self.id}: ********"
            return f"{self.id}: {self.printable_value}"
        return f"{self.id}: <not set>"


class StoreBase(ABC):
    def __init__(self, machine: "machines.Machine") -> None:
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

    @abstractmethod
    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        pass

    @property
    @abstractmethod
    def is_secret_store(self) -> bool:
        pass

    def backend_collision_error(self, folder: Path) -> None:
        msg = (
            f"Var folder {folder} exists but doesn't look like a {self.store_name} secret."
            "Potentially a leftover from another backend. Please delete it manually."
        )
        raise ClanError(msg)

    def rel_dir(self, generator_name: str, var_name: str, shared: bool = False) -> Path:
        if shared:
            return Path(f"shared/{generator_name}/{var_name}")
        return Path(f"per-machine/{self.machine.name}/{generator_name}/{var_name}")

    def directory(
        self, generator_name: str, var_name: str, shared: bool = False
    ) -> Path:
        return (
            Path(self.machine.flake_dir)
            / "vars"
            / self.rel_dir(generator_name, var_name, shared)
        )

    def set(
        self,
        generator_name: str,
        var_name: str,
        value: bytes,
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        if self.exists(generator_name, var_name, shared):
            if self.is_secret_store:
                old_val = None
                old_val_str = "********"
            else:
                old_val = self.get(generator_name, var_name, shared)
                old_val_str = string_repr(old_val)
        else:
            old_val = None
            old_val_str = "<not set>"
        new_file = self._set(generator_name, var_name, value, shared, deployed)
        if self.is_secret_store:
            print(f"Updated secret var {generator_name}/{var_name}\n")
        else:
            if value != old_val:
                print(
                    f"Updated var {generator_name}/{var_name}\n"
                    f"  old: {old_val_str}\n"
                    f"  new: {string_repr(value)}"
                )
            else:
                print(
                    f"Var {generator_name}/{var_name} remains unchanged: {old_val_str}"
                )
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
                        _store=self,
                        generator=gen_name,
                        name=f_name,
                        id=f"{gen_name}/{f_name}",
                        secret=file["secret"],
                        shared=generator["share"],
                        deployed=file["deploy"],
                    )
                )
        return all_vars
