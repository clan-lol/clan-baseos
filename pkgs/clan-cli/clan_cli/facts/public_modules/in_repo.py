from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine

from . import FactStoreBase


class FactStore(FactStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        self.works_remotely = False

    def set(self, service: str, name: str, value: bytes) -> Path | None:
        if self.machine.flake.is_local():
            fact_path = (
                self.machine.flake.path
                / "machines"
                / self.machine.name
                / "facts"
                / name
            )
            fact_path.parent.mkdir(parents=True, exist_ok=True)
            fact_path.touch()
            fact_path.write_bytes(value)
            return fact_path
        msg = f"in_flake fact storage is only supported for local flakes: {self.machine.flake}"
        raise ClanError(msg)

    def exists(self, service: str, name: str) -> bool:
        fact_path = (
            self.machine.flake_dir / "machines" / self.machine.name / "facts" / name
        )
        return fact_path.exists()

    # get a single fact
    def get(self, service: str, name: str) -> bytes:
        fact_path = (
            self.machine.flake_dir / "machines" / self.machine.name / "facts" / name
        )
        return fact_path.read_bytes()

    # get all facts
    def get_all(self) -> dict[str, dict[str, bytes]]:
        facts_folder = self.machine.flake_dir / "machines" / self.machine.name / "facts"
        facts: dict[str, dict[str, bytes]] = {}
        facts["TODO"] = {}
        if facts_folder.exists():
            for fact_path in facts_folder.iterdir():
                facts["TODO"][fact_path.name] = fact_path.read_bytes()
        return facts
