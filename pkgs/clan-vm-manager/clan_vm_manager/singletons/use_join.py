import logging
import threading
from collections.abc import Callable
from typing import Any, ClassVar, cast

import gi
from clan_cli.clan_uri import ClanURI
from clan_cli.history.add import HistoryEntry, add_history
from clan_cli.machines.machines import Machine

from clan_vm_manager.components.gkvstore import GKVStore
from clan_vm_manager.singletons.use_vms import ClanStore

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gio, GLib, GObject

log = logging.getLogger(__name__)


class JoinValue(GObject.Object):
    __gsignals__: ClassVar = {
        "join_finished": (GObject.SignalFlags.RUN_FIRST, None, []),
    }

    url: ClanURI
    entry: HistoryEntry | None

    def _join_finished_task(self) -> bool:
        self.emit("join_finished")
        return GLib.SOURCE_REMOVE

    def __init__(self, url: ClanURI) -> None:
        super().__init__()
        self.url: ClanURI = url
        self.entry: HistoryEntry | None = None

    def __join(self) -> None:
        new_entry = add_history(self.url)
        self.entry = new_entry
        GLib.idle_add(self._join_finished_task)

    def join(self) -> None:
        threading.Thread(target=self.__join).start()


class JoinList:
    """
    This is a singleton.
    It is initialized with the first call of use()
    """

    _instance: "None | JoinList" = None
    list_store: Gio.ListStore

    # Make sure the VMS class is used as a singleton
    def __init__(self) -> None:
        msg = "Call use() instead"
        raise RuntimeError(msg)

    @classmethod
    def use(cls: Any) -> "JoinList":
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls.list_store = Gio.ListStore.new(JoinValue)

            ClanStore.use().register_on_deep_change(cls._instance._rerender_join_list)

        return cls._instance

    def _rerender_join_list(
        self, source: GKVStore, position: int, removed: int, added: int
    ) -> None:
        self.list_store.items_changed(
            0, self.list_store.get_n_items(), self.list_store.get_n_items()
        )

    def is_empty(self) -> bool:
        return self.list_store.get_n_items() == 0

    def push(self, uri: ClanURI, after_join: Callable[[JoinValue], None]) -> None:
        """
        Add a join request.
        This method can add multiple join requests if called subsequently for each request.
        """

        value = JoinValue(uri)

        machine_id = Machine(uri.machine_name, uri.flake)
        machine_id_list = []

        for machine_obj in self.list_store:
            mvalue: ClanURI = cast(JoinValue, machine_obj).url
            machine = Machine(mvalue.machine_name, mvalue.flake)
            machine_id_list.append(machine.get_id())

        if machine_id in machine_id_list:
            log.info(f"Join request already exists: {value.url}. Ignoring.")
            return

        value.connect("join_finished", self._on_join_finished)
        value.connect("join_finished", after_join)

        self.list_store.append(value)

    def _on_join_finished(self, source: JoinValue) -> None:
        log.info(f"Join finished: {source.url}")
        self.discard(source)
        assert source.entry is not None
        ClanStore.use().push_history_entry(source.entry)

    def discard(self, value: JoinValue) -> None:
        (has, idx) = self.list_store.find(value)
        if has:
            self.list_store.remove(idx)
