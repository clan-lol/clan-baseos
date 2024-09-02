from clan_cli.vars._types import StoreBase


class FactStoreBase(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return False
