import importlib
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from clan_cli.api import API
from clan_cli.cmd import Log, run
from clan_cli.errors import ClanError
from clan_cli.facts.secret_modules import SecretStoreBase
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

from .automount import pause_automounting
from .list import list_possible_keymaps, list_possible_languages

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


@dataclass
class Disk:
    name: str
    device: str


@API.register
def flash_machine(
    machine: Machine,
    *,
    mode: str,
    disks: list[Disk],
    system_config: SystemConfig,
    dry_run: bool,
    write_efi_boot_entries: bool,
    debug: bool,
    no_udev: bool = False,
    extra_args: list[str] | None = None,
) -> None:
    devices = [Path(disk.device) for disk in disks]
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
            for disk in disks:
                disko_install.extend(["--disk", disk.name, disk.device])

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
