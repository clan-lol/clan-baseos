import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clan_cli.api import API
from clan_cli.dirs import TemplateType, clan_templates
from clan_cli.errors import ClanError
from clan_cli.machines.hardware import HardwareConfig, show_machine_hardware_config


@dataclass
class Placeholder:
    # Input name for the user
    label: str
    options: list[str] | None
    required: bool


@dataclass
class DiskSchema:
    name: str
    placeholders: dict[str, Placeholder]


log = logging.getLogger(__name__)


def disk_in_facter_report(hw_report: dict) -> bool:
    return "hardware" in hw_report and "disk" in hw_report["hardware"]


def get_best_unix_device_name(unix_device_names: list[str]) -> str:
    # find the first device name that is disk/by-id
    for device_name in unix_device_names:
        if "disk/by-id" in device_name:
            return device_name
    else:
        # if no by-id found, use the first device name
        return unix_device_names[0]


def hw_main_disk_options(hw_report: dict) -> list[str]:
    if not disk_in_facter_report(hw_report):
        msg = "hw_report doesnt include 'disk' information"
        raise ClanError(msg, description=f"{hw_report.keys()}")

    disks = hw_report["hardware"]["disk"]

    options: list[str] = []
    for disk in disks:
        unix_device_names = disk["unix_device_names"]
        device_name = get_best_unix_device_name(unix_device_names)
        options += [device_name]

    return options


# must be manually kept in sync with the ${clancore}/templates/disks directory
templates: dict[str, dict[str, Callable[[dict[str, Any]], Placeholder]]] = {
    "single-disk": {
        # Placeholders
        "mainDisk": lambda hw_report: Placeholder(
            label="Main disk", options=hw_main_disk_options(hw_report), required=True
        ),
    }
}


@API.register
def get_disk_schemas(base_path: Path, machine_name: str) -> dict[str, DiskSchema]:
    """
    Get the available disk schemas
    """
    disk_templates = clan_templates(TemplateType.DISK)
    disk_schemas = {}

    hw_report_path = HardwareConfig.NIXOS_FACTER.config_path(base_path, machine_name)
    if not hw_report_path.exists():
        msg = "Hardware configuration missing"
        raise ClanError(msg)

    hw_report = {}
    with hw_report_path.open("r") as hw_report_file:
        hw_report = json.load(hw_report_file)

    for disk_template in disk_templates.iterdir():
        if disk_template.is_file():
            schema_name = disk_template.stem
            if schema_name not in templates:
                msg = f"Disk schema {schema_name} not found in templates"
                raise ClanError(
                    msg,
                    description="This is an internal architecture problem. Because disk schemas dont define their own interface",
                )

            placeholder_getters = templates.get(schema_name)
            placeholders = {}

            if placeholder_getters:
                placeholders = {k: v(hw_report) for k, v in placeholder_getters.items()}

            disk_schemas[schema_name] = DiskSchema(
                name=schema_name, placeholders=placeholders
            )

    return disk_schemas


@API.register
def set_machine_disk_schema(
    base_path: Path,
    machine_name: str,
    schema_name: str,
    # Placeholders are used to fill in the disk schema
    placeholders: dict[str, str],
) -> None:
    """
    Set the disk placeholders of the template
    """
    # Assert the hw-config must exist before setting the disk
    hw_config = show_machine_hardware_config(base_path, machine_name)
    hw_config_path = hw_config.config_path(base_path, machine_name)

    if not hw_config_path.exists():
        msg = "Hardware configuration must exist before applying disk schema"
        raise ClanError(msg)

    if hw_config != HardwareConfig.NIXOS_FACTER:
        msg = "Hardware configuration must use type FACTER for applying disk schema automatically"
        raise ClanError(msg)

    disk_schema_path = clan_templates(TemplateType.DISK) / f"{schema_name}.nix"

    if not disk_schema_path.exists():
        msg = f"Disk schema not found at {disk_schema_path}"
        raise ClanError(msg)

    with disk_schema_path.open("r") as disk_template:
        print(disk_template.read())
