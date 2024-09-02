import argparse
import importlib
import json
import logging
import os
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import Log, run
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.dirs import module_root, user_cache_dir, vm_state_dir
from clan_cli.errors import ClanError
from clan_cli.facts.generate import generate_facts
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

from .inspect import VmConfig, inspect_vm
from .qemu import qemu_command
from .virtiofsd import start_virtiofsd
from .waypipe import start_waypipe

log = logging.getLogger(__name__)


def facts_to_nixos_config(facts: dict[str, dict[str, bytes]]) -> dict:
    nixos_config: dict = {}
    nixos_config["clanCore"] = {}
    nixos_config["clanCore"]["secrets"] = {}
    for service, service_facts in facts.items():
        nixos_config["clanCore"]["secrets"][service] = {}
        nixos_config["clanCore"]["secrets"][service]["facts"] = {}
        for fact, value in service_facts.items():
            nixos_config["clanCore"]["secrets"][service]["facts"][fact] = {
                "value": value.decode()
            }
    return nixos_config


# TODO move this to the Machines class
def build_vm(
    machine: Machine, tmpdir: Path, nix_options: list[str] = []
) -> dict[str, str]:
    # TODO pass prompt here for the GTK gui
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
        return vm_data
    except json.JSONDecodeError as e:
        raise ClanError(f"Failed to parse vm config: {e}")


def get_secrets(
    machine: Machine,
    tmpdir: Path,
) -> Path:
    secrets_dir = tmpdir / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)

    secret_facts_module = importlib.import_module(machine.secret_facts_module)
    secret_facts_store = secret_facts_module.SecretStore(machine=machine)

    generate_facts([machine], None, False)

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
        log=Log.BOTH,
        error_msg=f"Could not create disk image at {disk_img}",
    )

    return disk_img


def run_vm(
    vm: VmConfig,
    *,
    cachedir: Path | None = None,
    socketdir: Path | None = None,
    nix_options: list[str] = [],
    portmap: list[tuple[int, int]] = [],
) -> None:
    with ExitStack() as stack:
        machine = Machine(name=vm.machine_name, flake=vm.flake_url)
        log.debug(f"Creating VM for {machine}")

        # store the temporary rootfs inside XDG_CACHE_HOME on the host
        # otherwise, when using /tmp, we risk running out of memory
        cache = user_cache_dir() / "clan"
        cache.mkdir(exist_ok=True)

        if cachedir is None:
            cache_tmp = stack.enter_context(TemporaryDirectory(dir=cache))
            cachedir = Path(cache_tmp)

        if socketdir is None:
            socket_tmp = stack.enter_context(TemporaryDirectory())
            socketdir = Path(socket_tmp)

        # TODO: We should get this from the vm argument
        nixos_config = build_vm(machine, cachedir, nix_options)

        state_dir = vm_state_dir(str(vm.flake_url), machine.name)
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
        )

        packages = ["nixpkgs#qemu"]

        env = os.environ.copy()
        if vm.graphics and not vm.waypipe:
            packages.append("nixpkgs#virt-viewer")
            remote_viewer_mimetypes = module_root() / "vms" / "mimetypes"
            env["XDG_DATA_DIRS"] = (
                f"{remote_viewer_mimetypes}:{env.get('XDG_DATA_DIRS', '')}"
            )

        with (
            start_waypipe(qemu_cmd.vsock_cid, f"[{vm.machine_name}] "),
            start_virtiofsd(virtiofsd_socket),
        ):
            run(
                nix_shell(packages, qemu_cmd.args),
                env=env,
                log=Log.BOTH,
                error_msg=f"Could not start vm {machine}",
            )


def run_command(
    args: argparse.Namespace,
) -> None:
    machine_obj: Machine = Machine(args.machine, args.flake)

    vm: VmConfig = inspect_vm(machine=machine_obj)

    portmap = [(h, g) for h, g in (p.split(":") for p in args.publish)]

    run_vm(vm, nix_options=args.option, portmap=portmap)


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
    parser.set_defaults(func=lambda args: run_command(args))
