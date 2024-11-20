import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from clan_cli.errors import ClanError
from clan_cli.machines import machines

if TYPE_CHECKING:
    from .generate import Generator, Var

log = logging.getLogger(__name__)


def string_repr(value: bytes) -> str:
    try:
        return value.decode()
    except UnicodeDecodeError:
        return "<binary blob>"


@dataclass
class GeneratorUpdate:
    generator: str
    prompt_values: dict[str, str]


class StoreBase(ABC):
    def __init__(self, machine: "machines.Machine") -> None:
        self.machine = machine

    @property
    @abstractmethod
    def store_name(self) -> str:
        pass

    # get a single fact
    @abstractmethod
    def get(self, generator: "Generator", name: str) -> bytes:
        pass

    @abstractmethod
    def _set(
        self,
        generator: "Generator",
        var: "Var",
        value: bytes,
    ) -> Path | None:
        """
        override this method to implement the actual creation of the file
        """

    @abstractmethod
    def exists(self, generator: "Generator", name: str) -> bool:
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

    def rel_dir(self, generator: "Generator", var_name: str) -> Path:
        if generator.share:
            return Path(f"shared/{generator.name}/{var_name}")
        return Path(f"per-machine/{self.machine.name}/{generator.name}/{var_name}")

    def directory(self, generator: "Generator", var_name: str) -> Path:
        return Path(self.machine.flake_dir) / "vars" / self.rel_dir(generator, var_name)

    def set(
        self,
        generator: "Generator",
        var: "Var",
        value: bytes,
    ) -> Path | None:
        if self.exists(generator, var.name):
            if self.is_secret_store:
                old_val = None
                old_val_str = "********"
            else:
                old_val = self.get(generator, var.name)
                old_val_str = string_repr(old_val)
        else:
            old_val = None
            old_val_str = "<not set>"
        new_file = self._set(generator, var, value)
        if self.is_secret_store:
            print(f"Updated secret var {generator.name}/{var.name}\n")
        else:
            if value != old_val:
                print(
                    f"Updated var {generator.name}/{var.name}\n"
                    f"  old: {old_val_str}\n"
                    f"  new: {string_repr(value)}"
                )
            else:
                print(
                    f"Var {generator.name}/{var.name} remains unchanged: {old_val_str}"
                )
        return new_file

    def get_all(self) -> list["Var"]:
        all_vars = []
        for generator in self.machine.vars_generators:
            for var in generator.files:
                # only handle vars compatible to this store
                if self.is_secret_store != var.secret:
                    continue
                var.store(self)
                var.generator(generator)
                all_vars.append(var)
        return all_vars

    def get_invalidation_hash(self, generator: "Generator") -> str | None:
        """
        Return the invalidation hash that indicates if a generator needs to be re-run
        due to a change in its definition
        """
        hash_file = (
            self.machine.flake_dir / "vars" / generator.name / "invalidation_hash"
        )
        if not hash_file.exists():
            return None
        return hash_file.read_text().strip()

    def set_invalidation_hash(self, generator: "Generator", hash_str: str) -> None:
        """
        Store the invalidation hash that indicates if a generator needs to be re-run
        """
        hash_file = (
            self.machine.flake_dir / "vars" / generator.name / "invalidation_hash"
        )
        hash_file.parent.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(hash_str)

    def hash_is_valid(self, generator: "Generator") -> bool:
        """
        Check if the invalidation hash is up to date
        If the hash is not set in nix and hasn't been stored before, it is considered valid
            -> this provides backward and forward compatibility
        """
        stored_hash = self.get_invalidation_hash(generator)
        target_hash = generator.invalidation_hash
        # if the hash is neither set in nix nor on disk, it is considered valid (provides backwards compat)
        if target_hash is None and stored_hash is None:
            return True
        return stored_hash == target_hash
