from abc import abstractmethod
from pathlib import Path

from clan_cli.vars._types import StoreBase


class FactStoreBase(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return False

    @abstractmethod
    def set(
        self, service: str, name: str, value: bytes, shared: bool = False
    ) -> Path | None:
        pass
