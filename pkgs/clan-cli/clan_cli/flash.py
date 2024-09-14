import argparse
import importlib
import json
import logging
import os
import shutil
import textwrap
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .api import API
from .clan_uri import FlakeId
from .cmd import Log, run
from .completions import add_dynamic_completer, complete_machines
from .errors import ClanError
from .facts.secret_modules import SecretStoreBase
from .machines.machines import Machine
from .nix import nix_build, nix_shell

log = logging.getLogger(__name__)


@dataclass
class WifiConfig:
    ssid: str
    password: str


@dataclass
class SystemConfig:
    language: str | None = field(default=None)
    keymap: str | None = field(default=None)
    ssh_keys_path: list[str] | None = field(default=None)
    wifi_settings: list[WifiConfig] | None = field(default=None)


@contextmanager
def pause_automounting(
    devices: list[Path], no_udev: bool
) -> Generator[None, None, None]:
    """
    Pause automounting on the device for the duration of this context
    manager
    """
    if no_udev:
        yield None
        return

    if shutil.which("udevadm") is None:
        msg = "udev is required to disable automounting"
        log.warning(msg)
        yield None
        return

    if os.geteuid() != 0:
        msg = "root privileges are required to disable automounting"
        raise ClanError(msg)
    try:
        # See /usr/lib/udisks2/udisks2-inhibit
        rules_dir = Path("/run/udev/rules.d")
        rules_dir.mkdir(exist_ok=True)
        rule_files: list[Path] = []
        for device in devices:
            devpath: str = str(device)
            rule_file: Path = (
                rules_dir / f"90-udisks-inhibit-{devpath.replace('/', '_')}.rules"
            )
            with rule_file.open("w") as fd:
                print(
                    'SUBSYSTEM=="block", ENV{DEVNAME}=="'
                    + devpath
                    + '*", ENV{UDISKS_IGNORE}="1"',
                    file=fd,
                )
                fd.flush()
                os.fsync(fd.fileno())
            rule_files.append(rule_file)
        run(["udevadm", "control", "--reload"])
        run(["udevadm", "trigger", "--settle", "--subsystem-match=block"])

        yield None
    except Exception as ex:
        log.fatal(ex)
    finally:
        for rule_file in rule_files:
            rule_file.unlink(missing_ok=True)
        run(["udevadm", "control", "--reload"], check=False)
        run(["udevadm", "trigger", "--settle", "--subsystem-match=block"], check=False)


@API.register
def list_possible_keymaps() -> list[str]:
    cmd = nix_build(["nixpkgs#kbd"])
    result = run(cmd, log=Log.STDERR, error_msg="Failed to find kbdinfo")
    keymaps_dir = Path(result.stdout.strip()) / "share" / "keymaps"

    if not keymaps_dir.exists():
        msg = f"Keymaps directory '{keymaps_dir}' does not exist."
        raise ClanError(msg)

    keymap_files = []

    for _root, _, files in os.walk(keymaps_dir):
        for file in files:
            if file.endswith(".map.gz"):
                # Remove '.map.gz' ending
                name_without_ext = file[:-7]
                keymap_files.append(name_without_ext)

    return keymap_files


@API.register
def list_possible_languages() -> list[str]:
    cmd = nix_build(["nixpkgs#glibcLocales"])
    result = run(cmd, log=Log.STDERR, error_msg="Failed to find glibc locales")
    locale_file = Path(result.stdout.strip()) / "share" / "i18n" / "SUPPORTED"

    if not locale_file.exists():
        msg = f"Locale file '{locale_file}' does not exist."
        raise ClanError(msg)

    with locale_file.open() as f:
        lines = f.readlines()

    languages = []
    for line in lines:
        if line.startswith("#"):
            continue
        if "SUPPORTED-LOCALES" in line:
            continue
        # Split by '/' and take the first part
        language = line.split("/")[0].strip()
        languages.append(language)

    return languages


@API.register
def flash_machine(
    machine: Machine,
    *,
    mode: str,
    disks: dict[str, str],
    system_config: SystemConfig,
    dry_run: bool,
    write_efi_boot_entries: bool,
    debug: bool,
    no_udev: bool = False,
    extra_args: list[str] | None = None,
) -> None:
    devices = [Path(device) for device in disks.values()]
    with pause_automounting(devices, no_udev):
        if extra_args is None:
            extra_args = []
        system_config_nix: dict[str, Any] = {}

        if system_config.wifi_settings:
            wifi_settings = {}
            for wifi in system_config.wifi_settings:
                wifi_settings[wifi.ssid] = {"password": wifi.password}
            system_config_nix["clan"] = {"iwd": {"networks": wifi_settings}}

        if system_config.language:
            if system_config.language not in list_possible_languages():
                msg = (
                    f"Language '{system_config.language}' is not a valid language. "
                    f"Run 'clan flash --list-languages' to see a list of possible languages."
                )
                raise ClanError(msg)
            system_config_nix["i18n"] = {"defaultLocale": system_config.language}

        if system_config.keymap:
            if system_config.keymap not in list_possible_keymaps():
                msg = (
                    f"Keymap '{system_config.keymap}' is not a valid keymap. "
                    f"Run 'clan flash --list-keymaps' to see a list of possible keymaps."
                )
                raise ClanError(msg)
            system_config_nix["console"] = {"keyMap": system_config.keymap}

        if system_config.ssh_keys_path:
            root_keys = []
            for key_path in (Path(x) for x in system_config.ssh_keys_path):
                try:
                    root_keys.append(key_path.read_text())
                except OSError as e:
                    msg = f"Cannot read SSH public key file: {key_path}: {e}"
                    raise ClanError(msg) from e
            system_config_nix["users"] = {
                "users": {"root": {"openssh": {"authorizedKeys": {"keys": root_keys}}}}
            }

        secret_facts_module = importlib.import_module(machine.secret_facts_module)
        secret_facts_store: SecretStoreBase = secret_facts_module.SecretStore(
            machine=machine
        )
        with TemporaryDirectory() as tmpdir_:
            tmpdir = Path(tmpdir_)
            upload_dir = machine.secrets_upload_directory

            if upload_dir.startswith("/"):
                local_dir = tmpdir / upload_dir[1:]
            else:
                local_dir = tmpdir / upload_dir

            local_dir.mkdir(parents=True)
            secret_facts_store.upload(local_dir)
            disko_install = []

            if os.geteuid() != 0:
                if shutil.which("sudo") is None:
                    msg = "sudo is required to run disko-install as a non-root user"
                    raise ClanError(msg)
                wrapper = 'set -x; disko_install=$(command -v disko-install); exec sudo "$disko_install" "$@"'
                disko_install.extend(["bash", "-c", wrapper])

            disko_install.append("disko-install")
            if write_efi_boot_entries:
                disko_install.append("--write-efi-boot-entries")
            if dry_run:
                disko_install.append("--dry-run")
            if debug:
                disko_install.append("--debug")
            for name, device in disks.items():
                disko_install.extend(["--disk", name, device])

            disko_install.extend(["--extra-files", str(local_dir), upload_dir])
            disko_install.extend(["--flake", str(machine.flake) + "#" + machine.name])
            disko_install.extend(["--mode", str(mode)])
            disko_install.extend(
                [
                    "--system-config",
                    json.dumps(system_config_nix),
                ]
            )
            disko_install.extend(["--option", "dry-run", "true"])
            disko_install.extend(extra_args)

            cmd = nix_shell(
                ["nixpkgs#disko"],
                disko_install,
            )
            run(cmd, log=Log.BOTH, error_msg=f"Failed to flash {machine}")


@dataclass
class FlashOptions:
    flake: FlakeId
    machine: str
    disks: dict[str, str]
    dry_run: bool
    confirm: bool
    debug: bool
    mode: str
    write_efi_boot_entries: bool
    nix_options: list[str]
    no_udev: bool
    system_config: SystemConfig


class AppendDiskAction(argparse.Action):
    def __init__(self, option_strings: str, dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        option_string: str | None = None,
    ) -> None:
        disks = getattr(namespace, self.dest)
        assert isinstance(values, list), "values must be a list"
        disks[values[0]] = values[1]


def flash_command(args: argparse.Namespace) -> None:
    opts = FlashOptions(
        flake=args.flake,
        machine=args.machine,
        disks=args.disk,
        dry_run=args.dry_run,
        confirm=not args.yes,
        debug=args.debug,
        mode=args.mode,
        system_config=SystemConfig(
            language=args.language,
            keymap=args.keymap,
            ssh_keys_path=args.ssh_pubkey,
            wifi_settings=None,
        ),
        write_efi_boot_entries=args.write_efi_boot_entries,
        no_udev=args.no_udev,
        nix_options=args.option,
    )

    if args.list_languages:
        for language in list_possible_languages():
            print(language)
        return

    if args.list_keymaps:
        for keymap in list_possible_keymaps():
            print(keymap)
        return

    if args.wifi:
        opts.system_config.wifi_settings = [
            WifiConfig(ssid=ssid, password=password)
            for ssid, password in args.wifi.items()
        ]

    machine = Machine(opts.machine, flake=opts.flake)
    if opts.confirm and not opts.dry_run:
        disk_str = ", ".join(f"{name}={device}" for name, device in opts.disks.items())
        msg = f"Install {machine.name}"
        if disk_str != "":
            msg += f" to {disk_str}"
        msg += "? [y/N] "
        ask = input(msg)
        if ask != "y":
            return

    flash_machine(
        machine,
        mode=opts.mode,
        disks=opts.disks,
        system_config=opts.system_config,
        dry_run=opts.dry_run,
        debug=opts.debug,
        write_efi_boot_entries=opts.write_efi_boot_entries,
        no_udev=opts.no_udev,
        extra_args=opts.nix_options,
    )


def register_parser(parser: argparse.ArgumentParser) -> None:
    machines_parser = parser.add_argument(
        "machine",
        type=str,
        help="machine to install",
    )
    add_dynamic_completer(machines_parser, complete_machines)

    parser.add_argument(
        "--disk",
        type=str,
        nargs=2,
        metavar=("name", "value"),
        action=AppendDiskAction,
        help="device to flash to",
        default={},
    )
    mode_help = textwrap.dedent(
        """\
        Specify the mode of operation. Valid modes are: format, mount."
        Format will format the disk before installing.
        Mount will mount the disk before installing.
        Mount is useful for updating an existing system without losing data.
        """
    )
    parser.add_argument(
        "--wifi",
        type=str,
        nargs=2,
        metavar=("ssid", "password"),
        action=AppendDiskAction,
        help="wifi network to connect to",
        default={},
    )
    parser.add_argument(
        "--mode",
        type=str,
        help=mode_help,
        choices=["format", "mount"],
        default="format",
    )
    parser.add_argument(
        "--ssh-pubkey",
        type=Path,
        action="append",
        default=[],
        help="ssh pubkey file to add to the root user. Can be used multiple times",
    )
    parser.add_argument(
        "--language",
        type=str,
        help="system language",
    )
    parser.add_argument(
        "--list-languages",
        help="List possible languages",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--list-keymaps",
        help="List possible keymaps",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--no-udev",
        help="Disable udev rules to block automounting",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--keymap",
        type=str,
        help="system keymap",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="do not ask for confirmation",
        default=False,
    )
    parser.add_argument(
        "--dry-run",
        help="Only build the system, don't flash it",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--write-efi-boot-entries",
        help=textwrap.dedent(
            """
          Write EFI boot entries to the NVRAM of the system for the installed system.
          Specify this option if you plan to boot from this disk on the current machine,
          but not if you plan to move the disk to another machine.
        """
        ).strip(),
        default=False,
        action="store_true",
    )
    parser.set_defaults(func=flash_command)
