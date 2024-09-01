from abc import abstractmethod
from pathlib import Path

from clan_cli.vars._types import StoreBase


class SecretStoreBase(StoreBase):
    @abstractmethod
    def set(
        self,
        service: str,
        name: str,
        value: bytes,
        groups: list[str],
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        pass

    @property
    def is_secret_store(self) -> bool:
        return True

    def update_check(self) -> bool:
        return False

    @abstractmethod
    def upload(self, output_dir: Path) -> None:
        pass
