import logging
from collections.abc import Callable
from typing import Any, Generic, TypeVar

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GObject

log = logging.getLogger(__name__)


# Define type variables for key and value types
K = TypeVar("K")  # Key type
V = TypeVar(
    "V", bound=GObject.Object
)  # Value type, bound to GObject.GObject or its subclasses


class GKVStore(GObject.GObject, Gio.ListModel, Generic[K, V]):
    """
    A simple key-value store that implements the Gio.ListModel interface, with generic types for keys and values.
    Only use self[key] and del self[key] for accessing the items for better performance.
    This class could be optimized by having the objects remember their position in the list.
    """

    def __init__(self, gtype: type[V], key_gen: Callable[[V], K]) -> None:
        super().__init__()
        self.gtype = gtype
        self.key_gen = key_gen
        # From Python 3.7 onwards dictionaries are ordered by default
        self._items: dict[K, V] = {}

    ##################################
    #                                #
    #    Gio.ListStore Interface     #
    #                                #
    ##################################
    @classmethod
    def new(cls: Any, gtype: type[V]) -> "GKVStore":
        return cls.__new__(cls, gtype)

    def append(self, item: V) -> None:
        key = self.key_gen(item)
        self[key] = item

    def find(self, item: V) -> tuple[bool, int]:
        log.warning("Finding is O(n) in GKVStore. Better use indexing")
        for i, v in enumerate(self.values()):
            if v == item:
                return True, i
        return False, -1

    def find_with_equal_func(
        self, item: V, equal_func: Callable[[V, V], bool]
    ) -> tuple[bool, int]:
        log.warning("Finding is O(n) in GKVStore. Better use indexing")
        for i, v in enumerate(self.values()):
            if equal_func(v, item):
                return True, i
        return False, -1

    def find_with_equal_func_full(
        self, item: V, equal_func: Callable[[V, V, Any], bool], user_data: Any
    ) -> tuple[bool, int]:
        log.warning("Finding is O(n) in GKVStore. Better use indexing")
        for i, v in enumerate(self.values()):
            if equal_func(v, item, user_data):
                return True, i
        return False, -1

    def insert(self, position: int, item: V) -> None:
        log.warning("Inserting is O(n) in GKVStore. Better use append")
        log.warning(
            "This functions may have incorrect items_changed signal behavior. Please test it"
        )
        key = self.key_gen(item)
        if key in self._items:
            msg = "Key already exists in the dictionary"
            raise ValueError(msg)
        if position < 0 or position > len(self._items):
            msg = "Index out of range"
            raise IndexError(msg)

        # Temporary storage for items to be reinserted
        temp_list = [(k, self._items[k]) for k in list(self.keys())[position:]]

        # Delete items from the original dict
        for k in list(self.keys())[position:]:
            del self._items[k]

        # Insert the new key-value pair
        self._items[key] = item

        # Reinsert the items
        for _i, (k, v) in enumerate(temp_list):
            self._items[k] = v

        # Notify the model of the changes
        self.items_changed(position, 0, 1)

    def insert_sorted(
        self, item: V, compare_func: Callable[[V, V, Any], int], user_data: Any
    ) -> None:
        msg = "insert_sorted is not implemented in GKVStore"
        raise NotImplementedError(msg)

    def remove(self, position: int) -> None:
        if position < 0 or position >= self.get_n_items():
            return
        key = self.keys()[position]
        del self[key]
        self.items_changed(position, 1, 0)

    def remove_all(self) -> None:
        self._items.clear()
        self.items_changed(0, len(self._items), 0)

    def sort(self, compare_func: Callable[[V, V, Any], int], user_data: Any) -> None:
        msg = "sort is not implemented in GKVStore"
        raise NotImplementedError(msg)

    def splice(self, position: int, n_removals: int, additions: list[V]) -> None:
        msg = "splice is not implemented in GKVStore"
        raise NotImplementedError(msg)

    ##################################
    #                                #
    #    Gio.ListModel Interface     #
    #                                #
    ##################################
    def get_item(self, position: int) -> V | None:
        if position < 0 or position >= self.get_n_items():
            return None
        # Access items by index since OrderedDict does not support direct indexing
        key = list(self._items.keys())[position]
        return self._items[key]

    def do_get_item(self, position: int) -> V | None:
        return self.get_item(position)

    def get_item_type(self) -> Any:
        return self.gtype.__gtype__  # type: ignore[attr-defined]

    def do_get_item_type(self) -> GObject.GType:
        return self.get_item_type()

    def get_n_items(self) -> int:
        return len(self._items)

    def do_get_n_items(self) -> int:
        return self.get_n_items()

    ##################################
    #                                #
    #        Dict Interface          #
    #                                #
    ##################################
    def keys(self) -> list[K]:
        return list(self._items.keys())

    def values(self) -> list[V]:
        return list(self._items.values())

    def items(self) -> list[tuple[K, V]]:
        return list(self._items.items())

    def get(self, key: K, default: V | None = None) -> V | None:
        return self._items.get(key, default)

    # O(1) operation if the key does not exist, O(n) if it does
    def __setitem__(self, key: K, value: V) -> None:
        # If the key already exists, remove it O(n)
        if key in self._items:
            log.debug("Updating an existing key in GKVStore is O(n)")
            position = self.keys().index(key)
            self._items[key] = value
            self.items_changed(position, 1, 1)
        else:
            # Add the new key-value pair
            self._items[key] = value
            position = max(len(self._items) - 1, 0)
            self.items_changed(position, 0, 1)

    # O(n) operation
    def __delitem__(self, key: K) -> None:
        position = self.keys().index(key)
        del self._items[key]
        self.items_changed(position, 1, 0)

    def __len__(self) -> int:
        return len(self._items)

    # O(1) operation
    def __getitem__(self, key: K) -> V:  # type: ignore[override]
        return self._items[key]

    def __contains__(self, key: K) -> bool:  # type: ignore[override]
        return key in self._items

    def __str__(self) -> str:
        resp = "GKVStore(\n"
        for k, v in self._items.items():
            resp += f"{k}: {v}\n"
        resp += ")"
        return resp

    def __repr__(self) -> str:
        return self._items.__str__()

    ##################################
    #                                #
    #        Custom Methods          #
    #                                #
    ##################################
    def first(self) -> V:
        return self.values()[0]

    def last(self) -> V:
        return self.values()[-1]

    def register_on_change(
        self, callback: Callable[["GKVStore[K,V]", int, int, int], None]
    ) -> None:
        self.connect("items-changed", callback)
