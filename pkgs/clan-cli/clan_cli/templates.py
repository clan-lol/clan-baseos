import json
import logging
import os
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, NewType, TypedDict

from clan_cli.clan_uri import FlakeId  # Custom FlakeId type for Nix Flakes
from clan_cli.cmd import run  # Command execution utility
from clan_cli.errors import ClanError  # Custom exception for Clan errors
from clan_cli.nix import nix_eval  # Helper for Nix evaluation scripts

# Configure the logging module for debugging
log = logging.getLogger(__name__)

# Define custom types for better type annotations

InputName = NewType("InputName", str)


@dataclass
class InputVariant:
    input_name: InputName | None

    def is_self(self) -> bool:
        return self.input_name is None

    def __str__(self) -> str:
        return self.input_name or "self"


TemplateName = NewType("TemplateName", str)  # Represents the name of a template
TemplateType = Literal[
    "clan", "disko", "machine"
]  # Literal to restrict template type to specific values
ModuleName = NewType("ModuleName", str)  # Represents a module name in Clan exports


# TypedDict for ClanModule with required structure
class ClanModule(TypedDict):
    description: str  # Description of the module
    path: str  # Filepath of the module


# TypedDict for a Template with required structure
class Template(TypedDict):
    description: str  # Template description
    path: str  # Template path on disk


# TypedDict for the structure of templates organized by type
class TemplateTypeDict(TypedDict):
    disko: dict[TemplateName, Template]  # Templates under "disko" type
    clan: dict[TemplateName, Template]  # Templates under "clan" type
    machine: dict[TemplateName, Template]  # Templates under "machine" type


# TypedDict for a Clan attribute set (attrset) with templates and modules
class ClanAttrset(TypedDict):
    templates: TemplateTypeDict  # Organized templates by type
    modules: dict[ModuleName, ClanModule]  # Dictionary of modules by module name


# TypedDict to represent exported Clan attributes
class ClanExports(TypedDict):
    inputs: dict[
        InputName, ClanAttrset
    ]  # Input names map to their corresponding attrsets
    self: ClanAttrset  # The attribute set for the flake itself


# Helper function to get Clan exports (Nix flake outputs)
def get_clan_exports(clan_dir: FlakeId | None = None) -> ClanExports:
    # Check if the clan directory is provided, otherwise use the environment variable
    if not clan_dir:
        clan_core_path = os.environ.get("CLAN_CORE_PATH")
        if not clan_core_path:
            msg = "Environment var CLAN_CORE_PATH is not set, this shouldn't happen"
            raise ClanError(msg)
        # Use the clan core path from the environment variable
        clan_dir = FlakeId(clan_core_path)

    log.debug(f"Evaluating flake {clan_dir} for Clan attrsets")

    # Nix evaluation script to compute the relevant exports
    eval_script = f"""
        let
            self = builtins.getFlake "{clan_dir}";
            lib = self.inputs.nixpkgs.lib;
            inputsWithClan = lib.mapAttrs (
                _name: value: value.clan
            ) (lib.filterAttrs(_name: value: value ? "clan") self.inputs);
        in
            {{ inputs = inputsWithClan; self = self.clan or {{}}; }}
    """

    # Evaluate the Nix expression and run the command
    cmd = nix_eval(
        [
            "--json",  # Output the result as JSON
            "--impure",  # Allow impure evaluations (env vars or system state)
            "--expr",  # Evaluate the given Nix expression
            eval_script,
        ]
    )
    res = run(cmd).stdout  # Run the command and capture the JSON output
    return json.loads(res)  # Parse and return as a Python dictionary


# Dataclass to manage input prioritization for templates
@dataclass
class InputPrio:
    input_names: tuple[str, ...]  # Tuple of input names (ordered priority list)
    prioritize_self: bool = True  # Whether to prioritize "self" first

    # Static factory methods for specific prioritization strategies

    @staticmethod
    def self_only() -> "InputPrio":
        # Only consider "self" (no external inputs)
        return InputPrio(prioritize_self=True, input_names=())

    @staticmethod
    def try_inputs(input_names: tuple[str, ...]) -> "InputPrio":
        # Only consider the specified external inputs
        return InputPrio(prioritize_self=False, input_names=input_names)

    @staticmethod
    def try_self_then_inputs(input_names: tuple[str, ...]) -> "InputPrio":
        # Consider "self" first, then the specified external inputs
        return InputPrio(prioritize_self=True, input_names=input_names)


@dataclass
class FoundTemplate:
    input_variant: InputVariant
    name: TemplateName
    src: Template


def copy_from_nixstore(src: Path, dest: Path) -> None:
    if not src.is_dir():
        msg = f"The source path '{src}' is not a directory."
        raise ClanError(msg)

    # Walk through the source directory
    for root, _dirs, files in src.walk():
        relative_path = Path(root).relative_to(src)
        dest_dir = dest / relative_path

        dest_dir.mkdir(exist_ok=True)
        log.debug(f"Creating directory '{dest_dir}'")
        # Set permissions for directories
        dest_dir.chmod(stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)

        for file_name in files:
            src_file = Path(root) / file_name
            dest_file = dest_dir / file_name

            # Copy the file
            shutil.copy(src_file, dest_file)

            dest_file.chmod(stat.S_IWRITE | stat.S_IREAD)


@dataclass
class TemplateList:
    inputs: dict[InputName, dict[TemplateName, Template]] = field(default_factory=dict)
    self: dict[TemplateName, Template] = field(default_factory=dict)


def list_templates(
    template_type: TemplateType, clan_dir: FlakeId | None = None
) -> TemplateList:
    clan_exports = get_clan_exports(clan_dir)
    result = TemplateList()
    fallback: ClanAttrset = {
        "templates": {"disko": {}, "clan": {}, "machine": {}},
        "modules": {},
    }

    clan_templates = (
        clan_exports["self"]
        .get("templates", fallback["templates"])
        .get(template_type, {})
    )
    result.self = clan_templates
    for input_name, _attrset in clan_exports["inputs"].items():
        clan_templates = (
            clan_exports["inputs"]
            .get(input_name, fallback)["templates"]
            .get(template_type, {})
        )
        result.inputs[input_name] = {}
        for template_name, template in clan_templates.items():
            result.inputs[input_name][template_name] = template

    return result


# Function to retrieve a specific template from Clan exports
def get_template(
    template_name: TemplateName,
    template_type: TemplateType,
    *,
    input_prio: InputPrio | None = None,
    clan_dir: FlakeId | None = None,
) -> FoundTemplate:
    log.info(f"Searching for template '{template_name}' of type '{template_type}'")

    # Set default priority strategy if none is provided
    if input_prio is None:
        input_prio = InputPrio.try_self_then_inputs(("clan-core",))

    # Helper function to search for a specific template within a dictionary of templates
    def find_template(
        template_name: TemplateName, templates: dict[TemplateName, Template]
    ) -> Template | None:
        if template_name in templates:
            return templates[template_name]
        return None

    # Initialize variables for the search results
    template: Template | None = None
    input_name: InputName | None = None
    template_list = list_templates(template_type, clan_dir)

    # Step 1: Check "self" first, if prioritize_self is enabled
    if input_prio.prioritize_self:
        log.info(f"Checking 'self' for template '{template_name}'")
        template = find_template(template_name, template_list.self)

    # Step 2: Otherwise, check the external inputs if no match is found
    if not template and input_prio.input_names:
        log.info(f"Checking external inputs for template '{template_name}'")
        for input_name_str in input_prio.input_names:
            input_name = InputName(input_name_str)
            log.debug(f"Checking input '{input_name}' for template '{template_name}'")

            template = find_template(template_name, template_list.inputs[input_name])
            if template:
                log.debug(f"Found template '{template_name}' in input '{input_name}'")
                break  # Stop searching once the template is found

    # Step 3: Raise an error if the template wasn't found
    if not template:
        source = (
            f"inputs.{input_name}.clan.templates.{template_type}"
            if input_name  # Most recent "input_name"
            else f"flake.clan.templates.{template_type}"
        )
        msg = f"Template '{template_name}' not in '{source}' in '{clan_dir}'"
        raise ClanError(msg)

    return FoundTemplate(
        input_variant=InputVariant(input_name), src=template, name=template_name
    )
