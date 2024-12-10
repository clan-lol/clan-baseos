from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from clan_cli.vars._types import StoreBase

if TYPE_CHECKING:
    pass


class SecretStoreBase(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return True

    @abstractmethod
    def populate_dir(self, output_dir: Path) -> None:
        pass

    @abstractmethod
    def upload(self) -> None:
        pass
