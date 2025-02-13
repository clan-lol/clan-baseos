# Options are available in the following format:
# https://github.com/nixos/nixpkgs/blob/master/nixos/lib/make-options-doc/default.nix
#
# ```json
# {
# ...
# "fileSystems.<name>.options": {
#     "declarations": ["nixos/modules/tasks/filesystems.nix"],
#     "default": {
#       "_type": "literalExpression",
#       "text": "[\n  \"defaults\"\n]"
#     },
#     "description": "Options used to mount the file system.",
#     "example": {
#       "_type": "literalExpression",
#       "text": "[\n  \"data=journal\"\n]"
#     },
#     "loc": ["fileSystems", "<name>", "options"],
#     "readOnly": false,
#     "type": "non-empty (list of string (with check: non-empty))"
#     "relatedPackages": "- [`pkgs.tmux`](\n    https://search.nixos.org/packages?show=tmux&sort=relevance&query=tmux\n  )\n",
# }
# }
# ```

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clan_cli.api.modules import Frontmatter, extract_frontmatter, get_roles
from clan_cli.errors import ClanError

# Get environment variables
CLAN_CORE_PATH = Path(os.environ["CLAN_CORE_PATH"])
CLAN_CORE_DOCS = Path(os.environ["CLAN_CORE_DOCS"])
CLAN_MODULES_FRONTMATTER_DOCS = os.environ.get("CLAN_MODULES_FRONTMATTER_DOCS")
BUILD_CLAN_PATH = os.environ.get("BUILD_CLAN_PATH")

## Clan modules ##
# Some modules can be imported via nix natively
CLAN_MODULES_VIA_NIX = os.environ.get("CLAN_MODULES_VIA_NIX")
# Some modules can be imported via inventory
CLAN_MODULES_VIA_ROLES = os.environ.get("CLAN_MODULES_VIA_ROLES")


OUT = os.environ.get("out")


def sanitize(text: str) -> str:
    return text.replace(">", "\\>")


def replace_store_path(text: str) -> tuple[str, str]:
    res = text
    if text.startswith("/nix/store/"):
        res = "https://git.clan.lol/clan/clan-core/src/branch/main/" + str(
            Path(*Path(text).parts[4:])
        )
    name = Path(res).name
    return (res, name)


def render_option_header(name: str) -> str:
    return f"# {name}\n"


def join_lines_with_indentation(lines: list[str], indent: int = 4) -> str:
    """
    Joins multiple lines with a specified number of whitespace characters as indentation.

    Args:
    lines (list of str): The lines of text to join.
    indent (int): The number of whitespace characters to use as indentation for each line.

    Returns:
    str: The indented and concatenated string.
    """
    # Create the indentation string (e.g., four spaces)
    indent_str = " " * indent
    # Join each line with the indentation added at the beginning
    return "\n".join(indent_str + line for line in lines)


def sanitize_anchor(text: str) -> str:
    parts = text.split(".")
    res = []
    for part in parts:
        if "<" in part:
            continue
        res.append(part)

    return ".".join(res)


def render_option(
    name: str,
    option: dict[str, Any],
    level: int = 3,
    short_head: str | None = None,
) -> str:
    read_only = option.get("readOnly")

    res = f"""
{"#" * level} {sanitize(name) if short_head is None else sanitize(short_head)} {"{: #" + sanitize_anchor(name) + "}" if level > 1 else ""}

"""

    res += f"""
{f"**Attribute: `{name}`**" if short_head is not None else ""}

{"**Readonly**" if read_only else ""}

{option.get("description", "")}
"""
    if option.get("type"):
        res += f"""

**Type**: `{option["type"]}`

"""
    if option.get("default"):
        res += f"""
**Default**:

```nix
{option.get("default", {}).get("text") if option.get("default") else "No default set."}
```
        """
    example = option.get("example", {}).get("text")
    if example:
        example_indented = join_lines_with_indentation(example.split("\n"))
        res += f"""

???+ example

    ```nix
{example_indented}
    ```
"""
    if option.get("relatedPackages"):
        res += f"""
### Related Packages

{option["relatedPackages"]}
"""

    decls = option.get("declarations", [])
    if decls:
        source_path, name = replace_store_path(decls[0])
        res += f"""
:simple-git: [{name}]({source_path})
"""
        res += "\n\n"

    return res


def print_options(
    options_file: str, head: str, no_options: str, replace_prefix: str | None = None
) -> str:
    res = ""
    with (Path(options_file) / "share/doc/nixos/options.json").open() as f:
        options: dict[str, dict[str, Any]] = json.load(f)

        res += head if len(options.items()) else no_options
        for option_name, info in options.items():
            if replace_prefix:
                option_name = option_name.replace(replace_prefix + ".", "")

            res += render_option(option_name, info, 4)
    return res


def module_header(module_name: str, has_inventory_feature: bool = False) -> str:
    indicator = " 🔹" if has_inventory_feature else ""
    return f"# {module_name}{indicator}\n\n"


def module_nix_usage(module_name: str) -> str:
    return f"""## Usage via Nix

**This module can be also imported directly in your nixos configuration. Although it is recommended to use the [inventory](../../reference/nix-api/inventory.md) interface if available.**

Some modules are considered 'low-level' or 'expert modules' and are not available via the inventory interface.

```nix
{{config, lib, inputs, ...}}: {{
    imports = [ inputs.clan-core.clanModules.{module_name} ];
    # ...
}}
```

"""


clan_core_descr = """`clan.core` is always included in each machine `config`.
Your can customize your machines behavior with the configuration [options](#module-options) provided below.
"""

options_head = """
### Module Options

The following options are available for this module.
"""


def produce_clan_modules_frontmatter_docs() -> None:
    if not CLAN_MODULES_FRONTMATTER_DOCS:
        msg = f"Environment variables are not set correctly: $CLAN_CORE_DOCS={CLAN_CORE_DOCS}"
        raise ClanError(msg)

    if not OUT:
        msg = f"Environment variables are not set correctly: $out={OUT}"
        raise ClanError(msg)

    with Path(CLAN_MODULES_FRONTMATTER_DOCS).open() as f:
        options: dict[str, dict[str, Any]] = json.load(f)

        # header
        output = """# Frontmatter

Every clan module has a `frontmatter` section within its readme. It provides machine readable metadata about the module.

!!! example

    The used format is `TOML`

    The content is separated by `---` and the frontmatter must be placed at the very top of the `README.md` file.

    ```toml
    ---
    description = "A description of the module"
    categories = ["category1", "category2"]

    [constraints]
    roles.client.max = 10
    roles.server.min = 1
    ---
    # Readme content
    ...
    ```

"""

        output += """## Overview

This provides an overview of the available attributes of the `frontmatter` within the `README.md` of a clan module.

"""
        # for option_name, info in options.items():
        #     if option_name == "_module.args":
        #         continue
        #     output += render_option(option_name, info)
        root = options_to_tree(options, debug=True)
        for option in root.suboptions:
            output += options_docs_from_tree(option, init_level=2)

        outfile = Path(OUT) / "clanModules/frontmatter/index.md"
        outfile.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with outfile.open("w") as of:
            of.write(output)


def produce_clan_core_docs() -> None:
    if not CLAN_CORE_DOCS:
        msg = f"Environment variables are not set correctly: $CLAN_CORE_DOCS={CLAN_CORE_DOCS}"
        raise ClanError(msg)

    if not OUT:
        msg = f"Environment variables are not set correctly: $out={OUT}"
        raise ClanError(msg)

    # A mapping of output file to content
    core_outputs: dict[str, str] = {}
    with CLAN_CORE_DOCS.open() as f:
        options: dict[str, dict[str, Any]] = json.load(f)
        module_name = "clan-core"

        transform = {n.replace("clan.core.", ""): v for n, v in options.items()}
        split = split_options_by_root(transform)

        # Prepopulate the index file header
        indexfile = f"{module_name}/index.md"
        core_outputs[indexfile] = (
            module_header(module_name) + clan_core_descr + options_head
        )

        for submodule_name, split_options in split.items():
            outfile = f"{module_name}/{submodule_name}.md"
            print(
                f"[clan_core.{submodule_name}] Rendering option of: {submodule_name}... {outfile}"
            )
            init_level = 1
            root = options_to_tree(split_options, debug=True)

            print(f"Submodule {submodule_name} - suboptions", len(root.suboptions))

            module = root.suboptions[0]
            print("type", module.info.get("type"))

            module_type = module.info.get("type")

            if module_type is not None and "submodule" not in module_type:
                outfile = indexfile
                init_level = 2

            output = ""
            for option in root.suboptions:
                output += options_docs_from_tree(
                    option,
                    init_level=init_level,
                    prefix=["clan", "core"],
                )

            # Append the content
            if outfile not in core_outputs:
                core_outputs[outfile] = output
            else:
                core_outputs[outfile] += output

        for outfile, output in core_outputs.items():
            (Path(OUT) / outfile).parent.mkdir(parents=True, exist_ok=True)
            with (Path(OUT) / outfile).open("w") as of:
                of.write(output)


def render_roles(roles: list[str] | None, module_name: str) -> str:
    if roles:
        roles_list = "\n".join([f"    - `{r}`" for r in roles])
        return (
            f"""
### Roles

This module can be used via predefined roles

{roles_list}
"""
            """
Every role has its own configuration options. Which are each listed below.

For more information, see the [inventory guide](../../manual/inventory.md).

??? Example
    For example the `admin` module adds the following options globally to all machines where it is used.

    `clan.admin.allowedkeys`

    This means there are two equivalent ways to set the `allowedkeys` option. Either via a nixos module or via the inventory interface.
    **But it is recommended to keep together `imports` and `config` to preserve locality of the module configuration.**

    === "Inventory"

        ```nix
        clan-core.lib.buildClan {
            inventory.services = {
                admin.me = {
                    roles.default.machines = [ "jon" ];
                    config.allowedkeys = [ "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQD..." ];
                };
            };
        };
        ```

    === "NixOS"

        ```nix
        clan-core.lib.buildClan {
            machines = {
                jon = {
                    clan.admin.allowedkeys = [ "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQD..." ];
                    imports = [ clanModules.admin ];
                };
            };
        };
        ```
"""
        )
    return ""


clan_modules_descr = """Clan modules are [NixOS modules](https://wiki.nixos.org/wiki/NixOS_modules) which have been enhanced with additional features provided by Clan, with certain option types restricted to enable configuration through a graphical interface.

!!! note "🔹"
    Modules with this indicator support the [inventory](../../manual/inventory.md) feature.

"""


def render_categories(categories: list[str], frontmatter: Frontmatter) -> str:
    cat_info = frontmatter.categories_info
    res = """<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">"""
    for cat in categories:
        color = cat_info[cat]["color"]
        # description = cat_info[cat]["description"]
        res += f"""
    <div style="background-color: {color}; color: white; padding: 10px; border-radius: 20px; text-align: center;">
        {cat}
    </div>
"""
    res += "</div>"
    return res


def produce_clan_modules_docs() -> None:
    if not CLAN_MODULES_VIA_NIX:
        msg = f"Environment variables are not set correctly: $CLAN_MODULES_VIA_NIX={CLAN_MODULES_VIA_NIX}"
        raise ClanError(msg)

    if not CLAN_MODULES_VIA_ROLES:
        msg = f"Environment variables are not set correctly: $CLAN_MODULES_VIA_ROLES={CLAN_MODULES_VIA_ROLES}"
        raise ClanError(msg)

    if not CLAN_CORE_PATH:
        msg = f"Environment variables are not set correctly: $CLAN_CORE_PATH={CLAN_CORE_PATH}"
        raise ClanError(msg)

    if not OUT:
        msg = f"Environment variables are not set correctly: $out={OUT}"
        raise ClanError(msg)

    modules_index = "# Modules Overview\n\n"
    modules_index += clan_modules_descr
    modules_index += "## Overview\n\n"
    modules_index += '<div class="grid cards" markdown>\n\n'

    with Path(CLAN_MODULES_VIA_ROLES).open() as f2:
        role_links: dict[str, dict[str, str]] = json.load(f2)

    with Path(CLAN_MODULES_VIA_NIX).open() as f:
        links: dict[str, str] = json.load(f)

    for module_name, options_file in links.items():
        print(f"Rendering ClanModule: {module_name}")
        readme_file = CLAN_CORE_PATH / "clanModules" / module_name / "README.md"
        with readme_file.open() as f:
            readme = f.read()
            frontmatter: Frontmatter
            frontmatter, readme_content = extract_frontmatter(readme, str(readme_file))

        # skip if experimental feature enabled
        if "experimental" in frontmatter.features:
            print(f"Skipping {module_name}: Experimental feature")
            continue

        modules_index += build_option_card(module_name, frontmatter)

        ##### Print module documentation #####

        # 1. Header
        output = module_header(module_name, "inventory" in frontmatter.features)

        # 2. Description from README.md
        if frontmatter.description:
            output += f"**{frontmatter.description}**\n\n"

        # 3. Categories from README.md
        output += "## Categories\n\n"
        output += render_categories(frontmatter.categories, frontmatter)
        output += "\n---\n\n"

        # 3. README.md content
        output += f"{readme_content}\n"

        # 4. Usage
        ##### Print usage via Inventory #####

        # get_roles(str) -> list[str] | None
        # if not isinstance(options_file, str):
        roles = get_roles(CLAN_CORE_PATH / "clanModules" / module_name)
        if roles:
            # Render inventory usage
            output += """## Usage via Inventory\n\n"""
            output += render_roles(roles, module_name)
            for role in roles:
                role_options_file = role_links[module_name][role]
                # Abort if the options file is not found
                if not isinstance(role_options_file, str):
                    print(
                        f"Error: module: {module_name} in role: {role} - options file not found, Got {role_options_file}"
                    )
                    exit(1)

                no_options = f"""### Options of `{role}` role

**The `{module_name}` `{role}` doesnt offer / require any options to be set.**
"""

                heading = f"""### Options of `{role}` role

The following options are available when using the `{role}` role.
"""
                output += print_options(
                    role_options_file,
                    heading,
                    no_options,
                    replace_prefix=f"clan.{module_name}",
                )
        else:
            # No roles means no inventory usage
            output += """## Usage via Inventory

**This module cannot be used via the inventory interface.**
"""

        ##### Print usage via Nix / nixos #####
        if not isinstance(options_file, str):
            print(
                f"Skipping {module_name}: Cannot be used via import clanModules.{module_name}"
            )
            output += """## Usage via Nix

**This module cannot be imported directly in your nixos configuration.**

"""
        else:
            output += module_nix_usage(module_name)
            no_options = "** This module doesnt require any options to be set.**"
            output += print_options(options_file, options_head, no_options)

        outfile = Path(OUT) / f"clanModules/{module_name}.md"
        outfile.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with outfile.open("w") as of:
            of.write(output)

    modules_index += "</div>"
    modules_index += "\n"
    modules_outfile = Path(OUT) / "clanModules/index.md"

    with modules_outfile.open("w") as of:
        of.write(modules_index)


def build_option_card(module_name: str, frontmatter: Frontmatter) -> str:
    """
    Build the overview index card for each reference target option.
    """

    def indent_all(text: str, indent_size: int = 4) -> str:
        """
        Indent all lines in a string.
        """
        indent = " " * indent_size
        lines = text.split("\n")
        indented_text = indent + ("\n" + indent).join(lines)
        return indented_text

    def to_md_li(module_name: str, frontmatter: Frontmatter) -> str:
        md_li = (
            f"""-   **[{module_name}](./{"-".join(module_name.split(" "))}.md)**\n\n"""
        )
        md_li += f"""{indent_all("---", 4)}\n\n"""
        fmd = f"\n{frontmatter.description.strip()}" if frontmatter.description else ""
        md_li += f"""{indent_all(fmd, 4)}"""
        return md_li

    return f"{to_md_li(module_name, frontmatter)}\n\n"


def produce_build_clan_docs() -> None:
    if not BUILD_CLAN_PATH:
        msg = f"Environment variables are not set correctly: BUILD_CLAN_PATH={BUILD_CLAN_PATH}. Expected a path to the optionsJSON"
        raise ClanError(msg)

    if not OUT:
        msg = f"Environment variables are not set correctly: $out={OUT}"
        raise ClanError(msg)

    output = """# BuildClan

This provides an overview of the available arguments of the `clan` interface.

Each attribute is documented below

- **buildClan**: A function that takes an attribute set.`.

    ??? example "buildClan Example"

        ```nix
        buildClan {
            self = self;
            machines = {
                jon = { };
                sara = { };
            };
        };
        ```

- **flake-parts**: Each attribute can be defined via `clan.<attribute name>`. See our [flake-parts](../../manual/flake-parts.md) guide.

    ??? example "flake-parts Example"

        ```nix
        flake-parts.lib.mkFlake { inherit inputs; } ({
            systems = [];
            imports = [
                clan-core.flakeModules.default
            ];
            clan = {
                machines = {
                    jon = { };
                    sara = { };
                };
            };
        });
        ```

"""
    with Path(BUILD_CLAN_PATH).open() as f:
        options: dict[str, dict[str, Any]] = json.load(f)

        split = split_options_by_root(options)
        for option_name, options in split.items():
            # Skip underscore options
            if option_name.startswith("_"):
                continue
            # Skip inventory sub options
            # Inventory model has its own chapter
            if option_name.startswith("inventory."):
                continue

            print(f"[build_clan_docs] Rendering option of {option_name}...")
            root = options_to_tree(options)

            for option in root.suboptions:
                output += options_docs_from_tree(option, init_level=2)

    outfile = Path(OUT) / "nix-api/buildclan.md"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with Path.open(outfile, "w") as of:
        of.write(output)


def split_options_by_root(options: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Split the flat dictionary of options into a dict of which each entry will construct complete option trees.
    {
        "a": { Data }
        "a.b": { Data }
        "c": { Data }
    }
    ->
    {
        "a": {
            "a": { Data },
            "a.b": { Data }
        }
        "c": {
            "c": { Data }
        }
    }
    """
    res: dict[str, dict[str, Any]] = {}
    for key, value in options.items():
        parts = key.split(".")
        root = parts[0]
        if root not in res:
            res[root] = {}
        res[root][key] = value
    return res


@dataclass
class Option:
    name: str
    path: list[str]
    info: dict[str, Any]
    suboptions: list["Option"] = field(default_factory=list)


def produce_inventory_docs() -> None:
    if not BUILD_CLAN_PATH:
        msg = f"Environment variables are not set correctly: BUILD_CLAN_PATH={BUILD_CLAN_PATH}. Expected a path to the optionsJSON"
        raise ClanError(msg)

    if not OUT:
        msg = f"Environment variables are not set correctly: $out={OUT}"
        raise ClanError(msg)

    output = """# Inventory
This provides an overview of the available attributes of the `inventory` model.

It can be set via the `inventory` attribute of the [`buildClan`](./buildclan.md#inventory) function, or via the [`clan.inventory`](./buildclan.md#inventory) attribute of flake-parts.

"""
    # Inventory options are already included under the buildClan attribute
    # We just omitted them in the buildClan docs, because we want a separate output for the inventory model
    with Path(BUILD_CLAN_PATH).open() as f:
        options: dict[str, dict[str, Any]] = json.load(f)

        clan_root_option = options_to_tree(options)
        # Find the inventory options
        inventory_opt: None | Option = None
        for opt in clan_root_option.suboptions:
            if opt.name == "inventory":
                inventory_opt = opt
                break

        if not inventory_opt:
            print("No inventory options found.")
            exit(1)
        # Render the inventory options
        # This for loop excludes the root node
        for option in inventory_opt.suboptions:
            output += options_docs_from_tree(option, init_level=2)

    outfile = Path(OUT) / "nix-api/inventory.md"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with Path.open(outfile, "w") as of:
        of.write(output)


def option_short_name(option_name: str) -> str:
    parts = option_name.split(".")
    short_name = ""
    for part in parts[1:]:
        if "<" in part:
            continue
        short_name += ("." + part) if short_name else part
    return short_name


def options_to_tree(options: dict[str, Any], debug: bool = False) -> Option:
    """
    Convert the options dictionary to a tree structure.
    """

    # Helper function to create nested structure
    def add_to_tree(path_parts: list[str], info: Any, current_node: Option) -> None:
        if not path_parts:
            return

        name = path_parts[0]
        remaining_path = path_parts[1:]

        # Look for an existing suboption
        for sub in current_node.suboptions:
            if sub.name == name:
                add_to_tree(remaining_path, info, sub)
                return

        # If no existing suboption is found, create a new one
        new_option = Option(
            name=name,
            path=[*current_node.path, name],
            info={},  # Populate info only at the final leaf
        )
        current_node.suboptions.append(new_option)

        # If it's a leaf node, populate info
        if not remaining_path:
            new_option.info = info
        else:
            add_to_tree(remaining_path, info, new_option)

    # Create the root option
    root = Option(name="<root>", path=[], info={})

    # Process each key-value pair in the dictionary
    for key, value in options.items():
        path_parts = key.split(".")
        add_to_tree(path_parts, value, root)

    def print_tree(option: Option, level: int = 0) -> None:
        print("  " * level + option.name + ":", option.path)
        for sub in option.suboptions:
            print_tree(sub, level + 1)

    # Example usage
    if debug:
        print("Options tree:")
        print_tree(root)

    return root


def options_docs_from_tree(
    root: Option, init_level: int = 1, prefix: list[str] | None = None
) -> str:
    """
    Render the options from the tree structure.

    Args:
    root (Option): The root option node.
    init_level (int): The initial level of indentation.
    prefix (list str): Will be printed as common prefix of all attribute names.
    """

    def render_tree(option: Option, level: int = init_level) -> str:
        output = ""

        should_render = not option.name.startswith("<") and not option.name.startswith(
            "_"
        )
        if should_render:
            # short_name = option_short_name(option.name)
            path = ".".join(prefix + option.path) if prefix else ".".join(option.path)
            output += render_option(
                path,
                option.info,
                level=level,
                short_head=option.name,
            )

        for sub in option.suboptions:
            h_increment = 1 if should_render else 0

            if "_module" in sub.path:
                continue
            output += render_tree(sub, level + h_increment)

        return output

    md = render_tree(root)
    return md


if __name__ == "__main__":  #
    produce_clan_core_docs()

    produce_build_clan_docs()
    produce_inventory_docs()

    produce_clan_modules_docs()

    produce_clan_modules_frontmatter_docs()
