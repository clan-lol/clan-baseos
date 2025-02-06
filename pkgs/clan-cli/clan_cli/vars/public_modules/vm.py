import logging
from pathlib import Path

from clan_cli.dirs import vm_state_dir
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine
from clan_cli.vars._types import StoreBase
from clan_cli.vars.generate import Generator, Var

log = logging.getLogger(__name__)


class FactStore(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return False

    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        self.works_remotely = False
        self.dir = vm_state_dir(machine.flake.identifier, machine.name) / "facts"
        machine.debug(f"FactStore initialized with dir {self.dir}")

    @property
    def store_name(self) -> str:
        return "vm"

    def exists(self, generator: Generator, name: str) -> bool:
        fact_path = self.dir / generator.name / name
        return fact_path.exists()

    def _set(
        self,
        generator: Generator,
        var: Var,
        value: bytes,
    ) -> Path | None:
        fact_path = self.dir / generator.name / var.name
        fact_path.parent.mkdir(parents=True, exist_ok=True)
        fact_path.write_bytes(value)
        return None

    # get a single fact
    def get(self, generator: Generator, name: str) -> bytes:
        fact_path = self.dir / generator.name / name
        if fact_path.exists():
            return fact_path.read_bytes()
        msg = f"Fact {name} for service {generator.name} not found"
        raise ClanError(msg)

    def populate_dir(self, output_dir: Path, phases: list[str]) -> None:
        msg = "populate_dir is not implemented for public vars stores"
        raise NotImplementedError(msg)

    def upload(self, phases: list[str]) -> None:
        msg = "upload is not implemented for public vars stores"
        raise NotImplementedError(msg)
