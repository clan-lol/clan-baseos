import shutil
from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine
from clan_cli.vars.generate import Generator, Var

from . import FactStoreBase


class FactStore(FactStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        self.works_remotely = False

    @property
    def store_name(self) -> str:
        return "in_repo"

    def _set(
        self,
        generator: Generator,
        var: Var,
        value: bytes,
    ) -> Path | None:
        if not self.machine.flake.is_local():
            msg = f"in_flake fact storage is only supported for local flakes: {self.machine.flake}"
            raise ClanError(msg)
        folder = self.directory(generator, var.name)
        if folder.exists():
            if not (folder / "value").exists():
                # another backend has used that folder before -> error out
                self.backend_collision_error(folder)
            shutil.rmtree(folder)
        # re-create directory
        file_path = folder / "value"
        folder.mkdir(parents=True, exist_ok=True)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()
        file_path.write_bytes(value)
        return file_path

    # get a single fact
    def get(self, generator: Generator, name: str) -> bytes:
        return (self.directory(generator, name) / "value").read_bytes()

    def exists(self, generator: Generator, name: str) -> bool:
        return (self.directory(generator, name) / "value").exists()
