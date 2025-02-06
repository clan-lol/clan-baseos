import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import gi
from clan_cli.clan_uri import ClanURI
from clan_cli.flake import Flake
from clan_cli.history.add import HistoryEntry
from clan_cli.machines.machines import Machine

from clan_vm_manager import assets
from clan_vm_manager.components.gkvstore import GKVStore
from clan_vm_manager.components.vmobj import VMObject
from clan_vm_manager.singletons.use_views import ViewStack
from clan_vm_manager.views.logs import Logs

gi.require_version("GObject", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, GObject

log = logging.getLogger(__name__)


class VMStore(GKVStore):
    def __init__(self) -> None:
        super().__init__(VMObject, lambda vm: vm.data.flake.flake_attr)


class Emitter(GObject.GObject):
    __gsignals__: ClassVar = {
        "is_ready": (GObject.SignalFlags.RUN_FIRST, None, []),
    }


class ClanStore:
    _instance: "None | ClanStore" = None
    _clan_store: GKVStore[Flake, VMStore]

    _emitter: Emitter

    # set the vm that is outputting logs
    # build logs are automatically streamed to the logs-view
    _logging_vm: VMObject | None = None

    # Make sure the VMS class is used as a singleton
    def __init__(self) -> None:
        msg = "Call use() instead"
        raise RuntimeError(msg)

    @classmethod
    def use(cls: Any) -> "ClanStore":
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls._clan_store = GKVStore(
                VMStore, lambda store: store.first().data.flake.flake_url
            )
            cls._emitter = Emitter()

        return cls._instance

    def emit(self, signal: str) -> None:
        self._emitter.emit(signal)

    def connect(self, signal: str, cb: Callable[(...), Any]) -> None:
        self._emitter.connect(signal, cb)

    def set_logging_vm(self, ident: str) -> VMObject | None:
        vm = self.get_vm(ClanURI.from_str(f"clan://{ident}"))

        if vm is not None:
            self._logging_vm = vm

        return self._logging_vm

    def register_on_deep_change(
        self, callback: Callable[[GKVStore, int, int, int], None]
    ) -> None:
        """
        Register a callback that is called when a clan_store or one of the included VMStores changes
        """

        def on_vmstore_change(
            store: VMStore, position: int, removed: int, added: int
        ) -> None:
            callback(store, position, removed, added)

        def on_clanstore_change(
            store: "GKVStore", position: int, removed: int, added: int
        ) -> None:
            if added > 0:
                store.values()[position].register_on_change(on_vmstore_change)
            callback(store, position, removed, added)

        self.clan_store.register_on_change(on_clanstore_change)

    @property
    def clan_store(self) -> GKVStore[Flake, VMStore]:
        return self._clan_store

    def create_vm_task(self, vm: HistoryEntry) -> bool:
        self.push_history_entry(vm)
        return GLib.SOURCE_REMOVE

    def push_history_entry(self, entry: HistoryEntry) -> None:
        # TODO: We shouldn't do this here but in the list view
        if entry.flake.icon is None:
            icon: Path = assets.loc / "placeholder.jpeg"
        else:
            icon = Path(entry.flake.icon)

        def log_details(gfile: Gio.File) -> None:
            self.log_details(vm, gfile)

        vm = VMObject(icon=icon, data=entry, build_log_cb=log_details)
        self.push(vm)

    def log_details(self, vm: VMObject, gfile: Gio.File) -> None:
        views = ViewStack.use().view
        logs_view: Logs = views.get_child_by_name("logs")  # type: ignore

        def file_read_callback(
            source_object: Gio.File, result: Gio.AsyncResult, _user_data: Any
        ) -> None:
            try:
                # Finish the asynchronous read operation
                res = source_object.load_contents_finish(result)
                _success, contents, _etag_out = res

                # Convert the byte array to a string and print it
                logs_view.set_message(contents.decode("utf-8"))
            except Exception as e:
                print(f"Error reading file: {e}")

        # only one vm can output logs at a time
        if vm == self._logging_vm:
            gfile.load_contents_async(None, file_read_callback, None)

        # we cannot check this type, python is not smart enough

    def push(self, vm: VMObject) -> None:
        url = vm.data.flake.flake_url

        # Only write to the store if the Clan is not already in it
        # Every write to the KVStore rerenders bound widgets to the clan_store
        if url not in self.clan_store:
            log.debug(f"Creating new VMStore for {url}")
            vm_store = VMStore()
            vm_store.append(vm)
            self.clan_store[url] = vm_store
        else:
            vm_store = self.clan_store[url]
            machine = vm.data.flake.flake_attr
            old_vm = vm_store.get(machine)

            if old_vm:
                log.info(
                    f"VM {vm.data.flake.flake_attr} already exists in store. Updating data field."
                )
                old_vm.update(vm.data)
            else:
                log.debug(f"Appending VM {vm.data.flake.flake_attr} to store")
                vm_store.append(vm)

    def remove(self, vm: VMObject) -> None:
        del self.clan_store[vm.data.flake.flake_url][vm.data.flake.flake_attr]

    def get_vm(self, uri: ClanURI) -> None | VMObject:
        machine = Machine(uri.machine_name, uri.flake)
        vm_store = self.clan_store.get(machine.flake)

        if vm_store is None:
            return None
        vm = vm_store.get(str(machine.name), None)
        return vm

    def get_running_vms(self) -> list[VMObject]:
        return [
            vm
            for clan in self.clan_store.values()
            for vm in clan.values()
            if vm.is_running()
        ]

    def kill_all(self) -> None:
        for vm in self.get_running_vms():
            vm.kill()
