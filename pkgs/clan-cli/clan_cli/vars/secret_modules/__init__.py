from abc import abstractmethod
from pathlib import Path

from clan_cli.vars._types import StoreBase


class SecretStoreBase(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return True

    def needs_upload(self) -> bool:
        return True

    def ensure_machine_has_access(
        self, generator_name: str, name: str, shared: bool = False
    ) -> None:
        pass

    def needs_fix(
        self,
        generator_name: str,
        name: str,
        shared: bool,
    ) -> tuple[bool, str | None]:
        """
        Check if local state needs updating, eg. secret needs to be re-encrypted with new keys
        """
        return False, None

    def fix(
        self,
        generator_name: str,
        name: str,
        shared: bool,
    ) -> None:
        """
        Update local state, eg make sure secret is encrypted with correct keys
        """

    @abstractmethod
    def upload(self, output_dir: Path) -> None:
        pass
