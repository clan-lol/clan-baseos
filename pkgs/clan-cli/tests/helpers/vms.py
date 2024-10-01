import contextlib
import os
import socket
import sys
import threading
import traceback
from collections.abc import Iterator
from pathlib import Path
from time import sleep

from clan_cli.dirs import vm_state_dir
from clan_cli.errors import ClanError
from clan_cli.qemu.qga import QgaSession
from clan_cli.qemu.qmp import QEMUMonitorProtocol

from . import cli


def find_free_port() -> int:
    """Find an unused localhost port from 1024-65535 and return it."""
    with contextlib.closing(socket.socket(type=socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class VmThread(threading.Thread):
    def __init__(self, machine_name: str, ssh_port: int | None = None) -> None:
        super().__init__()
        self.machine_name = machine_name
        self.ssh_port = ssh_port
        self.exception: Exception | None = None
        self.daemon = True

    def run(self) -> None:
        try:
            cli.run(
                ["vms", "run", self.machine_name, "--publish", f"{self.ssh_port}:22"]
            )
        except Exception as ex:
            # print exception details
            print(traceback.format_exc(), file=sys.stderr)
            print(sys.exc_info()[2], file=sys.stderr)
            self.exception = ex


def run_vm_in_thread(machine_name: str, ssh_port: int | None = None) -> VmThread:
    # runs machine and prints exceptions
    if ssh_port is None:
        ssh_port = find_free_port()

    vm_thread = VmThread(machine_name, ssh_port)
    vm_thread.start()
    return vm_thread


# wait for qmp socket to exist
def wait_vm_up(machine_name: str, vm: VmThread, flake_url: str | None = None) -> None:
    if flake_url is None:
        flake_url = str(Path.cwd())
    socket_file = vm_state_dir(flake_url, machine_name) / "qmp.sock"
    timeout: float = 600
    while True:
        if vm.exception:
            msg = "VM failed to start"
            raise ClanError(msg) from vm.exception
        if timeout <= 0:
            msg = f"qmp socket {socket_file} not found. Is the VM running?"
            raise TimeoutError(msg)
        if socket_file.exists():
            break
        sleep(0.1)
        timeout -= 0.1


# wait for vm to be down by checking if qmp socket is down
def wait_vm_down(machine_name: str, vm: VmThread, flake_url: str | None = None) -> None:
    if flake_url is None:
        flake_url = str(Path.cwd())
    socket_file = vm_state_dir(flake_url, machine_name) / "qmp.sock"
    timeout: float = 300
    while socket_file.exists():
        if vm.exception:
            msg = "VM failed to start"
            raise ClanError(msg) from vm.exception
        if timeout <= 0:
            msg = f"qmp socket {socket_file} still exists. Is the VM down?"
            raise TimeoutError(msg)
        sleep(0.1)
        timeout -= 0.1


# wait for vm to be up then connect and return qmp instance
@contextlib.contextmanager
def qmp_connect(
    machine_name: str, vm: VmThread, flake_url: str | None = None
) -> Iterator[QEMUMonitorProtocol]:
    if flake_url is None:
        flake_url = str(Path.cwd())
    state_dir = vm_state_dir(flake_url, machine_name)
    wait_vm_up(machine_name, vm, flake_url)
    with QEMUMonitorProtocol(
        address=str(os.path.realpath(state_dir / "qmp.sock")),
    ) as qmp:
        qmp.connect()
        yield qmp


# wait for vm to be up then connect and return qga instance
@contextlib.contextmanager
def qga_connect(
    machine_name: str, vm: VmThread, flake_url: str | None = None
) -> Iterator[QgaSession]:
    if flake_url is None:
        flake_url = str(Path.cwd())
    state_dir = vm_state_dir(flake_url, machine_name)
    wait_vm_up(machine_name, vm, flake_url)

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        # try to reconnect a couple of times if connection refused
        socket_file = os.path.realpath(state_dir / "qga.sock")
        for _ in range(100):
            try:
                sock.connect(str(socket_file))
            except ConnectionRefusedError:
                sleep(0.1)
            else:
                break
            sock.connect(str(socket_file))
        yield QgaSession(sock)
    finally:
        sock.close()
