import argparse
import importlib
import json
import logging
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import CmdOut, Log, RunOpts, handle_io, run
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.dirs import module_root, user_cache_dir, vm_state_dir
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.facts.generate import generate_facts
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.qemu.qga import QgaSession
from clan_cli.qemu.qmp import QEMUMonitorProtocol

from .inspect import VmConfig, inspect_vm
from .qemu import qemu_command
from .virtiofsd import start_virtiofsd
from .waypipe import start_waypipe

log = logging.getLogger(__name__)


def facts_to_nixos_config(facts: dict[str, dict[str, bytes]]) -> dict:
    nixos_config: dict = {}
    nixos_config["clan"] = {}
    nixos_config["clan"]["core"] = {}
    nixos_config["clan"]["core"]["secrets"] = {}
    for service, service_facts in facts.items():
        nixos_config["clan"]["core"]["secrets"][service] = {}
        nixos_config["clan"]["core"]["secrets"][service]["facts"] = {}
        for fact, value in service_facts.items():
            nixos_config["clan"]["core"]["secrets"][service]["facts"][fact] = {
                "value": value.decode()
            }
    return nixos_config


# TODO move this to the Machines class
def build_vm(
    machine: Machine, tmpdir: Path, nix_options: list[str] | None = None
) -> dict[str, str]:
    # TODO pass prompt here for the GTK gui
    if nix_options is None:
        nix_options = []
    secrets_dir = get_secrets(machine, tmpdir)

    public_facts_module = importlib.import_module(machine.public_facts_module)
    public_facts_store = public_facts_module.FactStore(machine=machine)
    public_facts = public_facts_store.get_all()

    nixos_config_file = machine.build_nix(
        "config.system.clan.vm.create",
        extra_config=facts_to_nixos_config(public_facts),
        nix_options=nix_options,
    )
    try:
        vm_data = json.loads(Path(nixos_config_file).read_text())
        vm_data["secrets_dir"] = str(secrets_dir)
    except json.JSONDecodeError as e:
        msg = f"Failed to parse vm config: {e}"
        raise ClanError(msg) from e
    else:
        return vm_data


def get_secrets(
    machine: Machine,
    tmpdir: Path,
) -> Path:
    secrets_dir = tmpdir / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)

    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    secret_facts_store = secret_facts_module.SecretStore(machine=machine)

    generate_facts([machine])

    secret_facts_store.upload(secrets_dir)
    return secrets_dir


def prepare_disk(
    directory: Path,
    size: str = "1024M",
    file_name: str = "disk.img",
) -> Path:
    disk_img = directory / file_name
    cmd = nix_shell(
        ["nixpkgs#qemu"],
        [
            "qemu-img",
            "create",
            "-f",
            "qcow2",
            str(disk_img),
            size,
        ],
    )
    run(
        cmd,
        RunOpts(log=Log.BOTH, error_msg=f"Could not create disk image at {disk_img}"),
    )

    return disk_img


@contextmanager
def start_vm(
    args: list[str],
    packages: list[str],
    extra_env: dict[str, str],
    stdout: int | None = None,
    stderr: int | None = None,
    stdin: int | None = None,
) -> Iterator[subprocess.Popen]:
    env = os.environ.copy()
    env.update(extra_env)
    cmd = nix_shell(packages, args)
    log.debug(f"Starting VM with command: {cmd}")
    with subprocess.Popen(
        cmd, env=env, stdout=stdout, stderr=stderr, stdin=stdin
    ) as process:
        try:
            yield process
        finally:
            process.terminate()
            try:
                # Fix me: This should in future properly shutdown the VM using qmp
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


class QemuVm:
    def __init__(
        self,
        machine: Machine,
        process: subprocess.Popen,
        socketdir: Path,
    ) -> None:
        self.machine = machine
        self.process = process
        self.qmp_socket_file = socketdir / "qmp.sock"
        self.qga_socket_file = socketdir / "qga.sock"

    # wait for vm to be up then connect and return qmp instance
    @contextmanager
    def qmp_connect(self) -> Iterator[QEMUMonitorProtocol]:
        with QEMUMonitorProtocol(
            address=str(os.path.realpath(self.qmp_socket_file)),
        ) as qmp:
            qmp.connect()
            yield qmp

    @contextmanager
    def qga_connect(self, timeout_sec: float = 100) -> Iterator[QgaSession]:
        start_time = time.time()
        # try to reconnect a couple of times if connection refused
        session = None
        while time.time() - start_time < timeout_sec:
            try:
                session = QgaSession(str(self.qga_socket_file))
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
                continue
        if session is None:
            msg = (
                f"Timeout after {timeout_sec} seconds. Could not connect to QGA socket"
            )
            raise ClanError(msg)
        with session:
            yield session

    def wait_up(self, timeout_sec: float = 60) -> None:
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if self.process.poll() is not None:
                msg = "VM failed to start. Qemu process exited with code {self.process.returncode}"
                raise ClanError(msg)
            if self.qmp_socket_file.exists():
                break
            time.sleep(0.1)

    def wait_down(self) -> int:
        return self.process.wait()


@contextmanager
def spawn_vm(
    vm: VmConfig,
    *,
    cachedir: Path | None = None,
    socketdir: Path | None = None,
    nix_options: list[str] | None = None,
    portmap: dict[int, int] | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
    stdin: int | None = None,
) -> Iterator[QemuVm]:
    if portmap is None:
        portmap = {}
    if nix_options is None:
        nix_options = []
    with ExitStack() as stack:
        machine = Machine(name=vm.machine_name, flake=vm.flake_url)
        log.debug(f"Creating VM for {machine}")

        # store the temporary rootfs inside XDG_CACHE_HOME on the host
        # otherwise, when using /tmp, we risk running out of memory
        cache = user_cache_dir() / "clan"
        cache.mkdir(exist_ok=True)

        if cachedir is None:
            cache_tmp = stack.enter_context(
                TemporaryDirectory(prefix="vm-cache-", dir=cache)
            )
            cachedir = Path(cache_tmp)

        if socketdir is None:
            socket_tmp = stack.enter_context(TemporaryDirectory(prefix="vm-sockets-"))
            socketdir = Path(socket_tmp)

        # TODO: We should get this from the vm argument
        nixos_config = build_vm(machine, cachedir, nix_options)

        state_dir = vm_state_dir(vm.flake_url, machine.name)
        state_dir.mkdir(parents=True, exist_ok=True)

        # specify socket files for qmp and qga
        qmp_socket_file = socketdir / "qmp.sock"
        qga_socket_file = socketdir / "qga.sock"
        # Create symlinks to the qmp/qga sockets to be able to find them later.
        # This indirection is needed because we cannot put the sockets directly
        #   in the state_dir.
        # The reason is, qemu has a length limit of 108 bytes for the qmp socket
        #   path which is violated easily.
        qmp_link = state_dir / "qmp.sock"
        if os.path.lexists(qmp_link):
            qmp_link.unlink()
        qmp_link.symlink_to(qmp_socket_file)

        qga_link = state_dir / "qga.sock"
        if os.path.lexists(qga_link):
            qga_link.unlink()
        qga_link.symlink_to(qga_socket_file)

        rootfs_img = prepare_disk(cachedir)
        state_img = state_dir / "state.qcow2"
        if not state_img.exists():
            state_img = prepare_disk(
                directory=state_dir,
                file_name="state.qcow2",
                size="50G",
            )
        virtiofsd_socket = socketdir / "virtiofsd.sock"
        qemu_cmd = qemu_command(
            vm,
            nixos_config,
            secrets_dir=Path(nixos_config["secrets_dir"]),
            rootfs_img=rootfs_img,
            state_img=state_img,
            virtiofsd_socket=virtiofsd_socket,
            qmp_socket_file=qmp_socket_file,
            qga_socket_file=qga_socket_file,
            portmap=portmap,
            interactive=stdin is None,
        )

        packages = ["nixpkgs#qemu"]

        extra_env = {}
        if vm.graphics and not vm.waypipe.enable:
            packages.append("nixpkgs#virt-viewer")
            remote_viewer_mimetypes = module_root() / "vms" / "mimetypes"
            extra_env["XDG_DATA_DIRS"] = (
                f"{remote_viewer_mimetypes}:{os.environ.get('XDG_DATA_DIRS', '')}"
            )

        with (
            start_waypipe(qemu_cmd.vsock_cid, f"[{vm.machine_name}] "),
            start_virtiofsd(virtiofsd_socket),
            start_vm(
                qemu_cmd.args,
                packages,
                extra_env,
                stdout=stdout,
                stderr=stderr,
                stdin=stdin,
            ) as process,
        ):
            qemu_vm = QemuVm(machine, process, socketdir)
            qemu_vm.wait_up()

            try:
                yield qemu_vm
            finally:
                try:
                    with qemu_vm.qmp_connect() as qmp:
                        qmp.command("system_powerdown")
                    qemu_vm.wait_down()
                except OSError:
                    pass
                # TODO: add a timeout here instead of waiting indefinitely


@dataclass
class RuntimeConfig:
    cachedir: Path | None = None
    socketdir: Path | None = None
    nix_options: list[str] | None = None
    portmap: dict[int, int] | None = None
    command: list[str] | None = None
    no_block: bool = False


def run_vm(
    vm_config: VmConfig,
    runtime_config: RuntimeConfig,
) -> CmdOut:
    stdin = None
    if runtime_config.command is not None:
        stdin = subprocess.DEVNULL
    with (
        spawn_vm(
            vm_config,
            cachedir=runtime_config.cachedir,
            socketdir=runtime_config.socketdir,
            nix_options=runtime_config.nix_options,
            portmap=runtime_config.portmap,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=stdin,
        ) as vm,
        ThreadPoolExecutor(max_workers=1) as executor,
    ):
        future = executor.submit(
            handle_io,
            vm.process,
            prefix=f"[{vm_config.machine_name}] ",
            stdout=sys.stdout.buffer,
            stderr=sys.stderr.buffer,
            input_bytes=None,
            log=Log.BOTH,
        )
        args: list[str] = vm.process.args  # type: ignore[assignment]

        if runtime_config.command is not None:
            with vm.qga_connect() as qga:
                if runtime_config.no_block:
                    qga.run_nonblocking(runtime_config.command)
                else:
                    qga.run(runtime_config.command)

        stdout_buf, stderr_buf = future.result()

        rc = vm.wait_down()
        cmd_out = CmdOut(
            stdout=stdout_buf,
            stderr=stderr_buf,
            cwd=Path.cwd(),
            command_list=args,
            returncode=vm.process.returncode,
            msg=f"VM {vm_config.machine_name} exited with code {rc}",
            env={},
        )
        if rc != 0:
            raise ClanCmdError(cmd_out)
        return cmd_out


def run_command(
    args: argparse.Namespace,
) -> None:
    machine_obj: Machine = Machine(args.machine, args.flake)

    vm: VmConfig = inspect_vm(machine=machine_obj)

    if not os.environ.get("WAYLAND_DISPLAY"):
        vm.waypipe.enable = False

    portmap = dict(p.split(":") for p in args.publish)

    runtime_config = RuntimeConfig(
        nix_options=args.option,
        portmap=portmap,
        command=args.command,
        no_block=args.no_block,
    )

    run_vm(vm, runtime_config)


def register_run_parser(parser: argparse.ArgumentParser) -> None:
    machine_action = parser.add_argument(
        "machine", type=str, help="machine in the flake to run"
    )
    add_dynamic_completer(machine_action, complete_machines)
    # option: --publish 2222:22
    parser.add_argument(
        "--publish",
        "-p",
        action="append",
        type=str,
        default=[],
        help="Forward ports from host to guest",
    )
    parser.add_argument(
        "--no-block",
        action="store_true",
        help="Do no block when running the command",
        default=False,
    )
    parser.add_argument(
        "--command",
        "-c",
        nargs=argparse.REMAINDER,
        help="command to run in the vm",
    )
    parser.set_defaults(func=lambda args: run_command(args))
