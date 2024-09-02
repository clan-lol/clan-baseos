from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine

from . import FactStoreBase


class FactStore(FactStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        self.works_remotely = False
        self.per_machine_folder = (
            self.machine.flake_dir / "vars" / "per-machine" / self.machine.name
        )
        self.shared_folder = self.machine.flake_dir / "vars" / "shared"

    def _var_path(self, generator_name: str, name: str, shared: bool) -> Path:
        if shared:
            return self.shared_folder / generator_name / name
        return self.per_machine_folder / generator_name / name

    def set(
        self,
        generator_name: str,
        name: str,
        value: bytes,
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        if self.machine.flake.is_local():
            fact_path = self._var_path(generator_name, name, shared)
            fact_path.parent.mkdir(parents=True, exist_ok=True)
            fact_path.touch()
            fact_path.write_bytes(value)
            return fact_path
        msg = f"in_flake fact storage is only supported for local flakes: {self.machine.flake}"
        raise ClanError(msg)

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        return self._var_path(generator_name, name, shared).exists()

    # get a single fact
    def get(self, generator_name: str, name: str, shared: bool = False) -> bytes:
        return self._var_path(generator_name, name, shared).read_bytes()
