import logging
from pathlib import Path

from clan_cli.dirs import vm_state_dir
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine

from . import FactStoreBase

log = logging.getLogger(__name__)


class FactStore(FactStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        self.works_remotely = False
        self.dir = vm_state_dir(str(machine.flake), machine.name) / "facts"
        log.debug(f"FactStore initialized with dir {self.dir}")

    def exists(self, service: str, name: str, shared: bool = False) -> bool:
        fact_path = self.dir / service / name
        return fact_path.exists()

    def set(
        self,
        service: str,
        name: str,
        value: bytes,
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        fact_path = self.dir / service / name
        fact_path.parent.mkdir(parents=True, exist_ok=True)
        fact_path.write_bytes(value)
        return None

    # get a single fact
    def get(self, service: str, name: str, shared: bool = False) -> bytes:
        fact_path = self.dir / service / name
        if fact_path.exists():
            return fact_path.read_bytes()
        msg = f"Fact {name} for service {service} not found"
        raise ClanError(msg)
