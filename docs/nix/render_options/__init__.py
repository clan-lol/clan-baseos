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
from pathlib import Path
from typing import Any

from clan_cli.api.modules import Frontmatter, extract_frontmatter, get_roles
from clan_cli.errors import ClanError

# Get environment variables
CLAN_CORE_PATH = Path(os.environ["CLAN_CORE_PATH"])
CLAN_CORE_DOCS = Path(os.environ["CLAN_CORE_DOCS"])
CLAN_MODULES_FRONTMATTER_DOCS = os.environ.get("CLAN_MODULES_FRONTMATTER_DOCS")
CLAN_MODULES = os.environ.get("CLAN_MODULES")
BUILD_CLAN_PATH = os.environ.get("BUILD_CLAN_PATH")

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


def render_option(
    name: str, option: dict[str, Any], level: int = 3, short_head: str | None = None
) -> str:
    read_only = option.get("readOnly")

    res = f"""
{"#" * level} {sanitize(name) if short_head is None else sanitize(short_head)}

{f"**Attribute: `{name}`**" if short_head is not None else ""}

{"**Readonly**" if read_only else ""}

{option.get("description", "No description available.")}

**Type**: `{option["type"]}`

"""
    if option.get("default"):
        res += f"""
**Default**:

```nix
{option["default"]["text"] if option.get("default") else "No default set."}
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
        res += "\n"

    return res


def module_header(module_name: str, has_inventory_feature: bool = False) -> str:
    indicator = " 🔹" if has_inventory_feature else ""
    return f"# {module_name}{indicator}\n\n"


def module_usage(module_name: str) -> str:
    return f"""## Usage

To use this module, import it like th:

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

options_head = "\n## Module Options\n"


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

        output += """"## Overview

This provides an overview of the available attributes of the `frontmatter` within the `README.md` of a clan module.

"""
        for option_name, info in options.items():
            if option_name == "_module.args":
                continue
            output += render_option(option_name, info)

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
        for option_name, info in options.items():
            outfile = f"{module_name}/index.md"

            # Create separate files for nested options
            if len(option_name.split(".")) <= 3:
                # i.e. clan-core.clanDir
                output = core_outputs.get(
                    outfile,
                    module_header(module_name) + clan_core_descr + options_head,
                )
                output += render_option(option_name, info)
                # Update the content
                core_outputs[outfile] = output
            else:
                # Clan sub-options
                [_, sub] = option_name.split(".")[1:3]
                outfile = f"{module_name}/{sub}.md"
                # Get the content or write the header
                output = core_outputs.get(outfile, render_option_header(sub))
                output += render_option(option_name, info)
                # Update the content
                core_outputs[outfile] = output

        for outfile, output in core_outputs.items():
            (Path(OUT) / outfile).parent.mkdir(parents=True, exist_ok=True)
            with (Path(OUT) / outfile).open("w") as of:
                of.write(output)


def render_roles(roles: list[str] | None, module_name: str) -> str:
    if roles:
        roles_list = "\n".join([f"    - `{r}`" for r in roles])
        return f"""
## Inventory Roles

Predefined roles

{roles_list}

For more information, see the [inventory guide](../../manual/inventory.md).
"""
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
    if not CLAN_MODULES:
        msg = f"Environment variables are not set correctly: $out={CLAN_MODULES}"
        raise ClanError(msg)

    if not CLAN_CORE_PATH:
        msg = f"Environment variables are not set correctly: $CLAN_CORE_PATH={CLAN_CORE_PATH}"
        raise ClanError(msg)

    if not OUT:
        msg = f"Environment variables are not set correctly: $out={OUT}"
        raise ClanError(msg)

    with Path(CLAN_MODULES).open() as f:
        links: dict[str, str] = json.load(f)

    modules_index = "# Modules Overview\n\n"
    modules_index += clan_modules_descr
    modules_index += "## Overview\n\n"
    modules_index += '<div class="grid cards" markdown>\n\n'

    for module_name, options_file in links.items():
        readme_file = CLAN_CORE_PATH / "clanModules" / module_name / "README.md"
        with readme_file.open() as f:
            readme = f.read()
            frontmatter: Frontmatter
            frontmatter, readme_content = extract_frontmatter(readme, str(readme_file))

        modules_index += build_option_card(module_name, frontmatter)

        with (Path(options_file) / "share/doc/nixos/options.json").open() as f:
            options: dict[str, dict[str, Any]] = json.load(f)
            print(f"Rendering options for {module_name}...")
            output = module_header(module_name, "inventory" in frontmatter.features)

            if frontmatter.description:
                output += f"**{frontmatter.description}**\n\n"

            output += "## Categories\n\n"
            output += render_categories(frontmatter.categories, frontmatter)
            output += "\n---\n\n"

            output += f"{readme_content}\n"

            # get_roles(str) -> list[str] | None
            roles = get_roles(CLAN_CORE_PATH / "clanModules" / module_name)
            if roles:
                output += render_roles(roles, module_name)

            output += module_usage(module_name)

            output += options_head if len(options.items()) else ""
            for option_name, info in options.items():
                output += render_option(option_name, info)

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
            directory = self;
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
        for option_name, info in options.items():
            # Skip underscore options
            if option_name.startswith("_"):
                continue
            # Skip inventory sub options
            # Inventory model has its own chapter
            if option_name.startswith("inventory."):
                continue

            print(f"Rendering option of {option_name}...")
            output += render_option(option_name, info)

    outfile = Path(OUT) / "nix-api/buildclan.md"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with Path.open(outfile, "w") as of:
        of.write(output)


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

        def by_cat(item: tuple[str, dict[str, Any]]) -> Any:
            name, _info = item
            parts = name.split(".") if "." in name else ["root", "sub"]

            # Make everything fixed length.
            remain = 10 - len(parts)
            parts.extend(["A"] * remain)
            category = parts[1]
            # Sort by category,
            # then by length of the option,
            # then by the rest of the options
            comparator = (category, -remain, parts[2:9])
            return comparator

        seen_categories = set()
        for option_name, info in sorted(options.items(), key=by_cat):
            # Skip underscore options
            if option_name.startswith("_"):
                continue

            # Skip non inventory sub options
            if not option_name.startswith("inventory."):
                continue

            category = option_name.split(".")[1]

            heading_level = 3
            if category not in seen_categories:
                heading_level = 2
                seen_categories.add(category)

            parts = option_name.split(".")
            short_name = ""
            for part in parts[1:]:
                if "<" in part:
                    continue
                short_name += ("." + part) if short_name else part

            output += render_option(
                option_name, info, level=heading_level, short_head=short_name
            )

    outfile = Path(OUT) / "nix-api/inventory.md"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with Path.open(outfile, "w") as of:
        of.write(output)


if __name__ == "__main__":  #
    produce_build_clan_docs()
    produce_inventory_docs()

    produce_clan_core_docs()
    produce_clan_modules_docs()

    produce_clan_modules_frontmatter_docs()
