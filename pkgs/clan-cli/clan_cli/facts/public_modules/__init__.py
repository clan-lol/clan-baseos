from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import clan_cli.machines.machines as machines


class FactStoreBase(ABC):
    @abstractmethod
    def __init__(self, machine: machines.Machine) -> None:
        pass

    @abstractmethod
    def exists(self, service: str, name: str) -> bool:
        pass

    @abstractmethod
    def set(self, service: str, name: str, value: bytes) -> Path | None:
        pass

    # get a single fact
    @abstractmethod
    def get(self, service: str, name: str) -> bytes:
        pass

    # get all facts
    @abstractmethod
    def get_all(self) -> dict[str, dict[str, bytes]]:
        pass
