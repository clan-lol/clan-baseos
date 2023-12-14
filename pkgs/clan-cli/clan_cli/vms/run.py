import argparse
import json
import logging
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from ..dirs import module_root
from ..errors import ClanError
from ..nix import nix_build, nix_config, nix_shell
from .inspect import VmConfig, inspect_vm

log = logging.getLogger(__name__)


def graphics_options(vm: VmConfig) -> list[str]:
    if vm.wayland:
        # fmt: off
        return [
          "-nographic",
          "-vga", "none",
          "-device", "virtio-gpu-rutabaga,gfxstream-vulkan=on,cross-domain=on,hostmem=4G,wsi=headless",
        ]
        # fmt: on
    else:
        # fmt: off
        return [
            "-audiodev", "spice,id=audio0",
            "-device", "intel-hda",
            "-device", "hda-duplex,audiodev=audio0",
            "-display", "gtk,gl=on",
            "-device", "virtio-gpu-gl",
            "-display", "spice-app,gl=on",
            "-device", "virtio-serial-pci",
            "-chardev", "spicevmc,id=vdagent0,name=vdagent",
            "-device", "virtserialport,chardev=vdagent0,name=com.redhat.spice.0",
            "-device", "qemu-xhci,id=spicepass",
            "-chardev", "spicevmc,id=usbredirchardev1,name=usbredir",
            "-device", "usb-redir,chardev=usbredirchardev1,id=usbredirdev1",
            "-chardev", "spicevmc,id=usbredirchardev2,name=usbredir",
            "-device", "usb-redir,chardev=usbredirchardev2,id=usbredirdev2",
            "-chardev", "spicevmc,id=usbredirchardev3,name=usbredir",
            "-device", "usb-redir,chardev=usbredirchardev3,id=usbredirdev3",
            "-device", "pci-ohci,id=smartpass",
            "-device", "usb-ccid",
            "-chardev", "spicevmc,id=ccid,name=smartcard",
        ]
        # fmt: on


def qemu_command(
    vm: VmConfig,
    nixos_config: dict[str, str],
    xchg_dir: Path,
    secrets_dir: Path,
    disk_img: Path,
    wayland: bool,
) -> list[str]:
    kernel_cmdline = [
        (Path(nixos_config["toplevel"]) / "kernel-params").read_text(),
        f'init={nixos_config["toplevel"]}/init',
        f'regInfo={nixos_config["regInfo"]}/registration',
        # "console=hvc0,115200n8",
        "console=ttyS0,115200n8",  # serial
        # console=hvc0
    ]
    if vm.serial:
        # kernel_cmdline.append("console=tty0")
        kernel_cmdline.append("console=hvc0")

    # if not wayland or not vm.serial:
    #     kernel_cmdline.append("console=tty0")
    # fmt: off
    command = [
        "qemu-kvm",
        "-name", vm.flake_attr,
        "-m", f'{nixos_config["memorySize"]}M',
        "-smp", str(nixos_config["cores"]),
        "-cpu", "max",
        "-enable-kvm",
        "-device", "virtio-rng-pci",
        "-net", "nic,netdev=user.0,model=virtio",
        "-netdev", "user,id=user.0",
        "-virtfs", "local,path=/nix/store,security_model=none,mount_tag=nix-store",
        "-virtfs", f"local,path={xchg_dir},security_model=none,mount_tag=shared",
        "-virtfs", f"local,path={xchg_dir},security_model=none,mount_tag=xchg",
        "-virtfs", f"local,path={secrets_dir},security_model=none,mount_tag=secrets",
        "-drive", f"cache=writeback,file={disk_img},format=raw,id=drive1,if=none,index=1,werror=report",
        "-device", "virtio-blk-pci,bootindex=1,drive=drive1,serial=root",
        "-device", "virtio-keyboard",
        "-usb", "-device", "usb-tablet,bus=usb-bus.0",
        "-kernel", f'{nixos_config["toplevel"]}/kernel',
        "-initrd", nixos_config["initrd"],
        "-append", " ".join(kernel_cmdline),
    ]  # fmt: on

    if vm.graphics:
        command.extend(graphics_options(vm))

    if vm.serial:
        # command.append("-nographic") # weglassen?? kommt auf modus drauf an
        command.extend([
        "-serial", "null",
        "-device", "virtio-serial",
        "-chardev", "stdio,mux=on,id=char0,signal=off",
        "-mon", "chardev=char0,mode=readline",
        ]) # weglassen?? kommt auf modus drauf an
        #-serial null \
      # -device virtio-serial \
      # -chardev stdio,mux=on,id=char0,signal=off \
      # -mon chardev=char0,mode=readline \ 
      # terminal heisst dann anders
    # console=hvc0 
    # statt ttyS0
    return command


def get_vm_create_info(vm: VmConfig, nix_options: list[str]) -> dict[str, str]:
    config = nix_config()
    system = config["system"]

    clan_dir = vm.flake_url
    machine = vm.flake_attr
    cmd = nix_build(
        [
            f'{clan_dir}#clanInternals.machines."{system}"."{machine}".config.system.clan.vm.create',
            *nix_options,
        ]
    )
    proc = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise ClanError(
            f"Failed to build vm config: {shlex.join(cmd)} failed with: {proc.returncode}"
        )
    try:
        return json.loads(Path(proc.stdout.strip()).read_text())
    except json.JSONDecodeError as e:
        raise ClanError(f"Failed to parse vm config: {e}")


def generate_secrets(
    vm: VmConfig,
    nixos_config: dict[str, str],
    tmpdir: Path,
    log_fd: IO[str] | None,
) -> Path:
    secrets_dir = tmpdir / "secrets"
    secrets_dir.mkdir(exist_ok=True)

    env = os.environ.copy()
    env["CLAN_DIR"] = str(vm.flake_url)

    env["PYTHONPATH"] = str(":".join(sys.path))  # TODO do this in the clanCore module
    env["SECRETS_DIR"] = str(secrets_dir)

    # Only generate secrets for local clans
    if isinstance(vm.flake_url, Path) and vm.flake_url.is_dir():
        if Path(vm.flake_url).is_dir():
            subprocess.run(
                [nixos_config["generateSecrets"], vm.clan_name],
                env=env,
                check=False,
                stdout=log_fd,
                stderr=log_fd,
            )
        else:
            log.warning("won't generate secrets for non local clan")

    cmd = [nixos_config["uploadSecrets"]]
    res = subprocess.run(
        cmd,
        env=env,
        check=False,
        stdout=log_fd,
        stderr=log_fd,
    )
    if res.returncode != 0:
        raise ClanError(
            f"Failed to upload secrets: {shlex.join(cmd)} failed with {res.returncode}"
        )
    return secrets_dir


def prepare_disk(tmpdir: Path, log_fd: IO[str] | None) -> Path:
    disk_img = tmpdir / "disk.img"
    cmd = nix_shell(
        ["nixpkgs#qemu"],
        [
            "qemu-img",
            "create",
            "-f",
            "raw",
            str(disk_img),
            "1024M",
        ],
    )
    res = subprocess.run(
        cmd,
        check=False,
        stdout=log_fd,
        stderr=log_fd,
    )
    if res.returncode != 0:
        raise ClanError(
            f"Failed to create disk image: {shlex.join(cmd)} failed with {res.returncode}"
        )

    cmd = nix_shell(
        ["nixpkgs#e2fsprogs"],
        [
            "mkfs.ext4",
            "-L",
            "nixos",
            str(disk_img),
        ],
    )
    res = subprocess.run(
        cmd,
        check=False,
        stdout=log_fd,
        stderr=log_fd,
    )
    if res.returncode != 0:
        raise ClanError(
            f"Failed to create ext4 filesystem: {shlex.join(cmd)} failed with {res.returncode}"
        )
    return disk_img


def run_vm(
    vm: VmConfig, nix_options: list[str] = [], log_fd: IO[str] | None = None
) -> None:
    """
    log_fd can be used to stream the output of all commands to a UI
    """
    machine = vm.flake_attr
    log.debug(f"Creating VM for {machine}")

    # TODO: We should get this from the vm argument
    nixos_config = get_vm_create_info(vm, nix_options)

    flake_dir = Path(vm.flake_url)
    flake_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir_:
        tmpdir = Path(tmpdir_)
        xchg_dir = tmpdir / "xchg"
        xchg_dir.mkdir(exist_ok=True)

        secrets_dir = generate_secrets(vm, nixos_config, tmpdir, log_fd)
        disk_img = prepare_disk(tmpdir, log_fd)

        qemu_cmd = qemu_command(
            vm,
            nixos_config,
            xchg_dir=xchg_dir,
            secrets_dir=secrets_dir,
            disk_img=disk_img,
            wayland=vm.wayland,
        )

        if vm.wayland:
            packages = ["git+https://git.clan.lol/clan/clan-core.git#qemu-wayland"]
        else:
            packages = ["nixpkgs#qemu"]

        env = os.environ.copy()
        if vm.graphics and not vm.wayland:
            packages.append("nixpkgs#virt-viewer")
            remote_viewer_mimetypes = module_root() / "vms" / "mimetypes"
            env[
                "XDG_DATA_DIRS"
            ] = f"{remote_viewer_mimetypes}:{env.get('XDG_DATA_DIRS', '')}"

        import textwrap

        print("$ " + "\n".join(textwrap.wrap(shlex.join(qemu_cmd))))
        res = subprocess.run(
            nix_shell(packages, qemu_cmd),
            env=env,
            check=False,
            stdout=log_fd,
            stderr=log_fd,
        )
        if res.returncode != 0:
            raise ClanError(f"qemu failed with {res.returncode}")


@dataclass
class RunOptions:
    machine: str
    flake_url: str | None
    flake: Path
    nix_options: list[str] = field(default_factory=list)
    wayland: bool = False
    serial: bool = False


def run_command(args: argparse.Namespace) -> None:
    run_options = RunOptions(
        machine=args.machine,
        flake_url=args.flake_url,
        flake=args.flake or Path.cwd(),
        nix_options=args.option,
        wayland=args.wayland,
        serial=args.serial,
    )

    flake_url = run_options.flake_url or run_options.flake
    vm = inspect_vm(flake_url=flake_url, flake_attr=run_options.machine)
    # TODO: allow to set this in the config
    vm.wayland = run_options.wayland
    vm.serial = run_options.serial

    run_vm(vm, run_options.nix_options)


def register_run_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("machine", type=str, help="machine in the flake to run")
    parser.add_argument("--flake-url", type=str, help="flake url")
    parser.add_argument("--wayland", action="store_true", help="use wayland")
    parser.add_argument("--serial", action="store_true", help="use serial")
    parser.set_defaults(func=run_command)
