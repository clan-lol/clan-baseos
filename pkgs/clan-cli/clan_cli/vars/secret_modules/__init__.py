from abc import abstractmethod
from pathlib import Path

from clan_cli.vars._types import StoreBase


class SecretStoreBase(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return True

    def needs_upload(self) -> bool:
        return True

    @abstractmethod
    def upload(self, output_dir: Path) -> None:
        pass
