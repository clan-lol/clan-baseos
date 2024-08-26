import logging
import multiprocessing as mp
import os
import tempfile
import threading
import time
import weakref
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import IO, ClassVar

import gi
from clan_cli import vms
from clan_cli.clan_uri import ClanURI
from clan_cli.dirs import vm_state_dir
from clan_cli.history.add import HistoryEntry
from clan_cli.machines.machines import Machine
from clan_cli.vms.qemu import QMPWrapper

from clan_vm_manager.components.executor import MPProcess, spawn
from clan_vm_manager.singletons.toast import (
    InfoToast,
    SuccessToast,
    ToastOverlay,
    WarningToast,
)

gi.require_version("GObject", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, GObject, Gtk

log = logging.getLogger(__name__)


class VMObject(GObject.Object):
    # Define a custom signal with the name "vm_stopped" and a string argument for the message
    __gsignals__: ClassVar = {
        "vm_status_changed": (GObject.SignalFlags.RUN_FIRST, None, []),
        "vm_build_notify": (GObject.SignalFlags.RUN_FIRST, None, [bool, bool]),
    }

    def __init__(
        self,
        icon: Path,
        data: HistoryEntry,
        build_log_cb: Callable[[Gio.File], None],
    ) -> None:
        super().__init__()

        # Store the data from the history entry
        self.data: HistoryEntry = data
        self.build_log_cb = build_log_cb

        # Create a process object to store the VM process
        self.vm_process: MPProcess = MPProcess(
            "vm_dummy", mp.Process(), Path("./dummy")
        )
        self.build_process: MPProcess = MPProcess(
            "build_dummy", mp.Process(), Path("./dummy")
        )
        self._start_thread: threading.Thread = threading.Thread()
        self.machine: Machine | None = None
        self.qmp_wrap: QMPWrapper | None = None

        # Watcher to stop the VM
        self.KILL_TIMEOUT: int = 20  # seconds
        self._stop_thread: threading.Thread = threading.Thread()

        # Build progress bar vars
        self.progress_bar: Gtk.ProgressBar = Gtk.ProgressBar()
        self.progress_bar.hide()
        self.progress_bar.set_hexpand(True)  # Horizontally expand
        self.prog_bar_id: int = 0

        # Create a temporary directory to store the logs
        self.log_dir: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory(
            prefix="clan_vm-", suffix=f"-{self.data.flake.flake_attr}"
        )
        self._logs_id: int = 0
        self._log_file: IO[str] | None = None

        # To be able to set the switch state programmatically
        # we need to store the handler id returned by the connect method
        # and block the signal while we change the state. This is cursed.
        self.switch: Gtk.Switch = Gtk.Switch()
        self.switch_handler_id: int = self.switch.connect(
            "notify::active", self._on_switch_toggle
        )
        self.connect("vm_status_changed", self._on_vm_status_changed)

        # Make sure the VM is killed when the reference to this object is dropped
        self._finalizer: weakref.finalize = weakref.finalize(self, self._kill_ref_drop)

    def _vm_status_changed_task(self) -> bool:
        self.emit("vm_status_changed")
        return GLib.SOURCE_REMOVE

    def update(self, data: HistoryEntry) -> None:
        self.data = data

    def _on_vm_status_changed(self, source: "VMObject") -> None:
        # Signal may be emitted multiple times
        self.emit("vm_build_notify", self.is_building(), self.is_running())

        prev_state = self.switch.get_state()
        next_state = self.is_running() and not self.is_building()

        self.switch.set_state(next_state)
        if prev_state is False and next_state is True:
            ToastOverlay.use().add_toast_unique(
                SuccessToast(f"{source.data.flake.flake_attr} started").toast,
                "success.vm.start",
            )

        if self.switch.get_sensitive() is False and not self.is_building():
            self.switch.set_sensitive(True)

        exit_vm = self.vm_process.proc.exitcode
        exit_build = self.build_process.proc.exitcode
        exitc = exit_vm or exit_build
        if not self.is_running() and exitc != 0:
            with self.switch.handler_block(self.switch_handler_id):
                self.switch.set_active(False)
            log.error(f"VM exited with error. Exitcode: {exitc}")
            ToastOverlay.use().add_toast_unique(
                WarningToast(f"VM exited with error. Exitcode: {exitc}").toast,
                "warning.vm.exit",
            )

    def _on_switch_toggle(self, switch: Gtk.Switch, user_state: bool) -> None:
        if switch.get_active():
            switch.set_state(False)
            switch.set_sensitive(False)
            self.start()
        else:
            switch.set_state(True)
            self.shutdown()
            switch.set_sensitive(False)

    # We use a context manager to create the machine object
    # and make sure it is destroyed when the context is exited
    @contextmanager
    def _create_machine(self) -> Generator[Machine, None, None]:
        uri = ClanURI.from_str(
            url=str(self.data.flake.flake_url), machine_name=self.data.flake.flake_attr
        )
        if uri.flake.is_local():
            self.machine = Machine(
                name=self.data.flake.flake_attr,
                flake=uri.flake,
            )
        if uri.flake.is_remote():
            self.machine = Machine(
                name=self.data.flake.flake_attr,
                flake=uri.flake,
            )
        assert self.machine is not None

        if self.machine.flake.is_local():
            state_dir = vm_state_dir(
                flake_url=str(self.machine.flake.path), vm_name=self.machine.name
            )
        else:
            state_dir = vm_state_dir(
                flake_url=self.machine.flake.url, vm_name=self.machine.name
            )
        self.qmp_wrap = QMPWrapper(state_dir)
        assert self.machine is not None
        yield self.machine
        self.machine = None

    def _pulse_progress_bar_task(self) -> bool:
        if self.progress_bar.is_visible():
            self.progress_bar.pulse()
            return GLib.SOURCE_CONTINUE
        else:
            return GLib.SOURCE_REMOVE

    def __start(self) -> None:
        with self._create_machine() as machine:
            # Start building VM
            tstart = datetime.now()
            log.info(f"Building VM {self.get_id()}")
            log_dir = Path(str(self.log_dir.name))

            # Start the build process
            self.build_process = spawn(
                on_except=None,
                out_file=log_dir / "build.log",
                func=vms.run.build_vm,
                machine=machine,
                tmpdir=log_dir,
            )

            gfile = Gio.File.new_for_path(str(log_dir / "build.log"))
            # Gio documentation:
            # Obtains a file monitor for the given file.
            # If no file notification mechanism exists, then regular polling of the file is used.
            g_monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
            g_monitor.connect("changed", self.on_logs_changed)

            GLib.idle_add(self._vm_status_changed_task)
            self.switch.set_sensitive(True)
            # Start the logs watcher
            self._logs_id = GLib.timeout_add(
                50, self._get_logs_task, self.build_process
            )
            if self._logs_id == 0:
                log.error("Failed to start VM log watcher")
            log.debug(f"Starting logs watcher on file: {self.build_process.out_file}")

            # Start the progress bar and show it
            self.progress_bar.show()
            self.prog_bar_id = GLib.timeout_add(100, self._pulse_progress_bar_task)
            if self.prog_bar_id == 0:
                log.error("Couldn't spawn a progress bar task")

            # Wait for the build to finish then hide the progress bar
            self.build_process.proc.join()
            tend = datetime.now()
            log.info(f"VM {self.get_id()} build took {tend - tstart}s")
            self.progress_bar.hide()

            # Check if the VM was built successfully
            if self.build_process.proc.exitcode != 0:
                log.error(f"Failed to build VM {self.get_id()}")
                GLib.idle_add(self._vm_status_changed_task)
                return
            log.info(f"Successfully built VM {self.get_id()}")

            # Start the VM
            self.vm_process = spawn(
                on_except=None,
                out_file=Path(str(self.log_dir.name)) / "vm.log",
                func=vms.run.run_vm,
                vm=self.data.flake.vm,
                cachedir=log_dir,
                socketdir=log_dir,
            )
            log.debug(f"Started VM {self.get_id()}")
            GLib.idle_add(self._vm_status_changed_task)

            # Start the logs watcher
            self._logs_id = GLib.timeout_add(50, self._get_logs_task, self.vm_process)
            if self._logs_id == 0:
                log.error("Failed to start VM log watcher")
            log.debug(f"Starting logs watcher on file: {self.vm_process.out_file}")

            # Wait for the VM to stop
            self.vm_process.proc.join()
            log.debug(f"VM {self.get_id()} has stopped")
            GLib.idle_add(self._vm_status_changed_task)

    def on_logs_changed(
        self,
        monitor: Gio.FileMonitor,
        file: Gio.File,
        other_file: Gio.File,
        event_type: Gio.FileMonitorEvent,
    ) -> None:
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            # File was changed and the changes were written to disk
            # wire up the callback for setting the logs
            self.build_log_cb(file)

    def start(self) -> None:
        if self.is_running():
            log.warn("VM is already running. Ignoring start request")
            self.emit("vm_status_changed", self)
            return
        log.debug(f"VM state dir {self.log_dir.name}")
        self._start_thread = threading.Thread(target=self.__start)
        self._start_thread.start()

    def _get_logs_task(self, proc: MPProcess) -> bool:
        if not proc.out_file.exists():
            return GLib.SOURCE_CONTINUE

        if not self._log_file:
            try:
                self._log_file = open(proc.out_file)
            except Exception as ex:
                log.exception(ex)
                self._log_file = None
                return GLib.SOURCE_REMOVE

        line = os.read(self._log_file.fileno(), 4096)
        if len(line) != 0:
            print(line.decode("utf-8"), end="", flush=True)

        if not proc.proc.is_alive():
            log.debug("Removing logs watcher")
            self._log_file = None
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def is_running(self) -> bool:
        return self._start_thread.is_alive()

    def is_building(self) -> bool:
        return self.build_process.proc.is_alive()

    def is_shutting_down(self) -> bool:
        return self._stop_thread.is_alive()

    def get_id(self) -> str:
        return f"{self.data.flake.flake_url}#{self.data.flake.flake_attr}"

    def __stop(self) -> None:
        log.info(f"Stopping VM {self.get_id()}")

        start_time = datetime.now()
        while self.is_running():
            diff = datetime.now() - start_time
            if diff.seconds > self.KILL_TIMEOUT:
                log.error(
                    f"VM {self.get_id()} has not stopped after {self.KILL_TIMEOUT}s. Killing it"
                )
                self.vm_process.kill_group()
                break
            if self.is_building():
                log.info(f"VM {self.get_id()} is still building. Killing it")
                self.build_process.kill_group()
                break
            if not self.machine:
                log.error(f"Machine object is None. Killing VM {self.get_id()}")
                self.vm_process.kill_group()
                break

            # Try to shutdown the VM gracefully using QMP
            try:
                assert self.qmp_wrap is not None
                with self.qmp_wrap.qmp_ctx() as qmp:
                    qmp.command("system_powerdown")
            except Exception as ex:
                log.debug(f"QMP command 'system_powerdown' ignored. Error: {ex}")

            # Try 20 times to stop the VM
            time.sleep(self.KILL_TIMEOUT / 20)
        GLib.idle_add(self._vm_status_changed_task)
        log.debug(f"VM {self.get_id()} has stopped")

        ToastOverlay.use().add_toast_unique(
            InfoToast(f"Stopped {self.get_id()}").toast, "info.vm.exit"
        )

    def shutdown(self) -> None:
        if not self.is_running():
            log.warning("VM not running. Ignoring shutdown request.")
            self.emit("vm_status_changed", self)
            return
        if self.is_shutting_down():
            log.warning("Shutdown already in progress")
            self.emit("vm_status_changed", self)
            return
        self._stop_thread = threading.Thread(target=self.__stop)
        self._stop_thread.start()

    def _kill_ref_drop(self) -> None:
        if self.is_running():
            log.warning("Killing VM due to reference drop")
            self.kill()

    def kill(self) -> None:
        if not self.is_running():
            log.warning(f"Tried to kill VM {self.get_id()} is not running")
            return
        log.info(f"Killing VM {self.get_id()} now")

        if self.vm_process.proc.is_alive():
            self.vm_process.kill_group()

        if self.build_process.proc.is_alive():
            self.build_process.kill_group()

    def read_whole_log(self) -> str:
        if not self.vm_process.out_file.exists():
            log.error(f"Log file {self.vm_process.out_file} does not exist")
            return ""
        return self.vm_process.out_file.read_text()

    def __str__(self) -> str:
        return f"VM({self.get_id()})"

    def __repr__(self) -> str:
        return self.__str__()
