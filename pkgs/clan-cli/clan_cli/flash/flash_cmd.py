import argparse
import logging
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clan_cli.clan_uri import FlakeId
from clan_cli.completions import add_dynamic_completer, complete_machines
from clan_cli.machines.machines import Machine

from .flash import Disk, SystemConfig, flash_machine

log = logging.getLogger(__name__)


@dataclass
class FlashOptions:
    flake: FlakeId
    machine: str
    disks: list[Disk]
    dry_run: bool
    confirm: bool
    debug: bool
    mode: str
    write_efi_boot_entries: bool
    nix_options: list[str]
    system_config: SystemConfig


class AppendDiskAction(argparse.Action):
    def __init__(self, option_strings: str, dest: str, **kwargs: Any) -> None:
        super().__init__(option_strings, dest, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,  # Updated type hint
        option_string: str | None = None,
    ) -> None:
        # Ensure 'values' is a sequence of two elements
        if not (
            isinstance(values, Sequence)
            and not isinstance(values, str)
            and len(values) == 2
        ):
            msg = "Two values must be provided for a 'disk'"
            raise ValueError(msg)

        # Use the same logic as before, ensuring 'values' is a sequence
        current_disks: list[Disk] = getattr(namespace, self.dest, [])
        disk_name, disk_device = values
        current_disks.append(Disk(name=disk_name, device=disk_device))
        setattr(namespace, self.dest, current_disks)


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
        ),
        write_efi_boot_entries=args.write_efi_boot_entries,
        nix_options=args.option,
    )

    machine = Machine(opts.machine, flake=opts.flake)
    if opts.confirm and not opts.dry_run:
        disk_str = ", ".join(f"{disk.name}={disk.device}" for disk in opts.disks)
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
        extra_args=opts.nix_options,
    )


def register_flash_write_parser(parser: argparse.ArgumentParser) -> None:
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
        metavar=("name", "device"),
        action=AppendDiskAction,
        help="device to flash to",
        default=[],
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
