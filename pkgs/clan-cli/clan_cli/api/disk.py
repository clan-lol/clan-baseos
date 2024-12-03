import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from clan_cli.api import API
from clan_cli.api.modules import Frontmatter, extract_frontmatter
from clan_cli.dirs import TemplateType, clan_templates
from clan_cli.errors import ClanError
from clan_cli.git import commit_file
from clan_cli.machines.hardware import HardwareConfig, show_machine_hardware_config

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


def hw_main_disk_options(hw_report: dict) -> list[str] | None:
    options: list[str] = []
    if not disk_in_facter_report(hw_report):
        return None

    disks = hw_report["hardware"]["disk"]

    for disk in disks:
        unix_device_names = disk["unix_device_names"]
        device_name = get_best_unix_device_name(unix_device_names)
        options += [device_name]

    return options


@dataclass
class Placeholder:
    # Input name for the user
    label: str
    options: list[str] | None
    required: bool


@dataclass
class DiskSchema:
    name: str
    readme: str
    frontmatter: Frontmatter
    placeholders: dict[str, Placeholder]


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
def get_disk_schemas(
    base_path: Path, machine_name: str | None = None
) -> dict[str, DiskSchema]:
    """
    Get the available disk schemas
    """
    disk_templates = clan_templates(TemplateType.DISK)
    disk_schemas = {}
    hw_report = {}

    if machine_name is not None:
        hw_report_path = HardwareConfig.NIXOS_FACTER.config_path(
            base_path, machine_name
        )
        if not hw_report_path.exists():
            msg = "Hardware configuration missing"
            raise ClanError(msg)
        with hw_report_path.open("r") as hw_report_file:
            hw_report = json.load(hw_report_file)

    for disk_template in disk_templates.iterdir():
        if disk_template.is_dir():
            schema_name = disk_template.stem
            if schema_name not in templates:
                msg = f"Disk schema {schema_name} not found in templates {templates.keys()}"
                raise ClanError(
                    msg,
                    description="This is an internal architecture problem. Because disk schemas dont define their own interface",
                )

            placeholder_getters = templates.get(schema_name)
            placeholders = {}

            if placeholder_getters:
                placeholders = {k: v(hw_report) for k, v in placeholder_getters.items()}

            raw_readme = (disk_template / "README.md").read_text()
            frontmatter, readme = extract_frontmatter(
                raw_readme, f"{disk_template}/README.md"
            )

            disk_schemas[schema_name] = DiskSchema(
                name=schema_name,
                placeholders=placeholders,
                readme=readme,
                frontmatter=frontmatter,
            )

    return disk_schemas


@API.register
def set_machine_disk_schema(
    base_path: Path,
    machine_name: str,
    schema_name: str,
    # Placeholders are used to fill in the disk schema
    # Use get disk schemas to get the placeholders and their options
    placeholders: dict[str, str],
    force: bool = False,
) -> None:
    """ "
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

    disk_schema_path = clan_templates(TemplateType.DISK) / f"{schema_name}/default.nix"

    if not disk_schema_path.exists():
        msg = f"Disk schema not found at {disk_schema_path}"
        raise ClanError(msg)

    # Check that the placeholders are valid
    disk_schema = get_disk_schemas(base_path, machine_name)[schema_name]
    # check that all required placeholders are present
    for placeholder_name, schema_placeholder in disk_schema.placeholders.items():
        if schema_placeholder.required and placeholder_name not in placeholders:
            msg = f"Required placeholder {placeholder_name} - {schema_placeholder} missing"
            raise ClanError(msg)

    # For every placeholder check that the value is valid
    for placeholder_name, placeholder_value in placeholders.items():
        ph = disk_schema.placeholders.get(placeholder_name)
        # Unknown placeholder
        if not ph:
            msg = (
                f"Placeholder {placeholder_name} not found in disk schema {schema_name}"
            )
            raise ClanError(
                msg,
                description=f"Available placeholders: {disk_schema.placeholders.keys()}",
            )

        # Invalid value. Check if the value is one of the provided options
        if ph.options and placeholder_value not in ph.options:
            msg = (
                f"Invalid value {placeholder_value} for placeholder {placeholder_name}"
            )
            raise ClanError(msg, description=f"Valid options: {ph.options}")

    header = f"""# ---
# schema = "{schema_name}"
# ---
# This file was automatically generated!
# CHANGING this configuration requires wiping and reinstalling the machine
"""
    with disk_schema_path.open("r") as disk_template:
        config_str = disk_template.read()
        for placeholder_name, placeholder_value in placeholders.items():
            config_str = config_str.replace(
                r"{{" + placeholder_name + r"}}", placeholder_value
            )

        # Custom replacements
        config_str = config_str.replace(r"{{uuid}}", str(uuid4()).replace("-", ""))

        # place disko.nix alongside the hw-config
        disko_file_path = hw_config_path.parent.joinpath("disko.nix")
        if disko_file_path.exists() and not force:
            msg = f"Disk schema already exists at {disko_file_path}"
            raise ClanError(msg, description="Use 'force' to overwrite")

        with disko_file_path.open("w") as disk_config:
            disk_config.write(header)
            disk_config.write(config_str)

        commit_file(
            disko_file_path,
            base_path,
            commit_message=f"Set disk schema of machine: {machine_name} to {schema_name}",
        )
