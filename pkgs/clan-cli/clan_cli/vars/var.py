from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from clan_cli.vars.generate import Generator

    from ._types import StoreBase


@dataclass
class Var:
    id: str
    name: str
    secret: bool = True
    deploy: bool = False
    owner: str = "root"
    group: str = "root"
    needed_for_users: bool = False

    # TODO: those shouldn't be set here
    _store: "StoreBase | None" = None
    _generator: "Generator | None" = None

    def store(self, store: "StoreBase") -> None:
        self._store = store

    def generator(self, generator: "Generator") -> None:
        self._generator = generator

    @property
    def value(self) -> bytes:
        assert self._store is not None
        assert self._generator is not None
        if not self._store.exists(self._generator, self.name):
            msg = f"Var {self.id} has not been generated yet"
            raise ValueError(msg)
        # try decode the value or return <binary blob>
        return self._store.get(self._generator, self.name)

    @property
    def printable_value(self) -> str:
        try:
            return self.value.decode()
        except UnicodeDecodeError:
            return "<binary blob>"

    def set(self, value: bytes) -> None:
        assert self._store is not None
        assert self._generator is not None
        self._store.set(self._generator, self, value)

    @property
    def exists(self) -> bool:
        assert self._store is not None
        assert self._generator is not None
        return self._store.exists(self._generator, self.name)

    def __str__(self) -> str:
        if self._store is None or self._generator is None:
            return f"{self.id}: <not initialized>"

        # TODO: we don't want __str__ with side effects, this should be a separate method
        if self._store.exists(self._generator, self.name):
            if self.secret:
                return f"{self.id}: ********"
            return f"{self.id}: {self.printable_value}"
        return f"{self.id}: <not set>"

    @classmethod
    def from_json(cls: type["Var"], generator_name: str, data: dict[str, Any]) -> "Var":
        return cls(
            id=f"{generator_name}/{data['name']}",
            name=data["name"],
            secret=data["secret"],
            deploy=data["deploy"],
            owner=data.get("owner", "root"),
            group=data.get("group", "root"),
            needed_for_users=data.get("neededForUsers", False),
        )
