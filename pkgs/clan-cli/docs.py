import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from clan_cli import create_parser


@dataclass
class Option:
    name: str
    description: str
    default: str | None = None
    metavar: str | None = None
    epilog: str | None = None

    def to_md_li(self, delim: str = "-") -> str:
        # - **--example, `--e`**: <PATH> {description} (Default: `default` {epilog})
        md_li = f"{delim} **{self.name}**: "
        md_li += f"`<{self.metavar}>` " if self.metavar else ""
        md_li += f"(Default: `{self.default}`) " if self.default else ""
        md_li += indent_next(
            f"\n{self.description.strip()}" if self.description else ""
        )
        # md_li += indent_next(f"\n{self.epilog.strip()}" if self.epilog else "")

        return md_li


@dataclass
class Subcommand:
    name: str
    description: str | None = None
    epilog: str | None = None

    def to_md_li(self, parent: "Category") -> str:
        md_li = f"""- **[{self.name}](#{"-".join(parent.title.split(" "))}-{self.name})**: """
        md_li += indent_next(f"{self.description.strip()} " if self.description else "")
        md_li += indent_next(f"\n{self.epilog.strip()}" if self.epilog else "")

        return md_li


icon_table = {
    "backups": ":material-backup-restore: ",
    "config": ":material-shape-outline: ",
    "facts": ":simple-databricks: ",
    "flakes": ":material-snowflake: ",
    "flash": ":material-flash: ",
    "history": ":octicons-history-24: ",
    "machines": ":octicons-devices-24: ",
    "secrets": ":octicons-passkey-fill-24: ",
    "ssh": ":material-ssh: ",
    "vms": ":simple-virtualbox: ",
}


@dataclass
class Category:
    title: str
    # Flags such as --example, -e
    options: list[Option]
    # Positionals such as 'cmd <example>'
    positionals: list[Option]

    # Subcommands such as clan 'machines'
    # In contrast to an option it is a command that can have further children
    subcommands: list[Subcommand]
    # Description of the command
    description: str | None = None
    # Additional information, typically displayed at the bottom
    epilog: str | None = None
    # What level of depth the category is at (i.e. 'backups list' is 2, 'backups' is 1, 'clan' is 0)
    level: int = 0

    def to_md_li(self, level: int = 1) -> str:
        md_li = ""
        if level == self.level:
            icon = icon_table.get(self.title, "")
            md_li += f"""-   **[{icon}{self.title}](./{"-".join(self.title.split(" "))}.md)**\n\n"""
            md_li += f"""{indent_all("---", 4)}\n\n"""
            md_li += indent_all(
                f"{self.description.strip()}\n" if self.description else "", 4
            )

        return md_li


def epilog_to_md(text: str) -> str:
    """
    Convert the epilog to md
    """
    after_examples = False
    md = ""
    # md += text
    for line in text.split("\n"):
        if line.strip() == "Examples:":
            after_examples = True
            md += "### Examples"
            md += "\n"
        else:
            if after_examples:
                if line.strip().startswith("$"):
                    md += f"`{line}`"
                    md += "\n"
                    md += "\n"
                else:
                    # TODO: check, if the link is already a markdown link, only convert if not
                    # if contains_https_link(line):
                    #     line = convert_to_markdown_link(line)
                    md += line
                    md += "\n"
            else:
                md += line
                md += "\n"
    return md


import re


def contains_https_link(line: str) -> bool:
    pattern = r"https://\S+"
    return re.search(pattern, line) is not None


def convert_to_markdown_link(line: str) -> str:
    pattern = r"(https://\S+)"

    # Replacement pattern to convert it to a Markdown link
    return re.sub(pattern, r"[\1](\1)", line)


def indent_next(text: str, indent_size: int = 4) -> str:
    """
    Indent all lines in a string except the first line.
    This is useful for adding multiline texts a lists in Markdown.
    """
    indent = " " * indent_size
    lines = text.split("\n")
    indented_text = lines[0] + ("\n" + indent).join(lines[1:])
    return indented_text


def indent_all(text: str, indent_size: int = 4) -> str:
    """
    Indent all lines in a string.
    """
    indent = " " * indent_size
    lines = text.split("\n")
    indented_text = indent + ("\n" + indent).join(lines)
    return indented_text


def get_subcommands(
    parser: argparse.ArgumentParser,
    to: list[Category],
    level: int = 0,
    prefix: list[str] | None = None,
) -> tuple[list[Option], list[Option], list[Subcommand]]:
    """
    Generate Markdown documentation for an argparse.ArgumentParser instance including its subcommands.

    :param parser: The argparse.ArgumentParser instance.
    :param level: Current depth of subcommand.
    :return: Markdown formatted documentation as a string.
    """

    # Document each argument
    # --flake --option --debug, etc.
    if prefix is None:
        prefix = []
    flag_options: list[Option] = []
    positional_options: list[Option] = []
    subcommands: list[Subcommand] = []

    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._HelpAction):  # noqa: SLF001
            # Pseudoaction that holds the help message
            continue

        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            continue  # Subparsers handled separately

        option_strings = ", ".join(action.option_strings)
        if option_strings:
            flag_options.append(
                Option(
                    name=option_strings,
                    description=action.help if action.help else "",
                    default=action.default if action.default is not None else "",
                    metavar=f"{action.metavar}" if action.metavar else "",
                )
            )

        if not option_strings:
            # Positional arguments
            positional_options.append(
                Option(
                    name=action.dest,
                    description=action.help if action.help else "",
                    default=action.default if action.default is not None else "",
                    metavar=f"{action.metavar}" if action.metavar else "",
                )
            )

    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            subparsers: dict[str, argparse.ArgumentParser] = action.choices

            for name, subparser in subparsers.items():
                parent = " ".join(prefix)

                sub_command = Subcommand(name=name, description=subparser.description)
                subcommands.append(sub_command)

                (_options, _positionals, _subcommands) = get_subcommands(
                    parser=subparser, to=to, level=level + 1, prefix=[*prefix, name]
                )

                to.append(
                    Category(
                        title=f"{parent} {name}",
                        description=subparser.description,
                        # epilog=subparser.epilog,
                        level=level,
                        options=_options,
                        positionals=_positionals,
                        subcommands=_subcommands,
                    )
                )

    return (flag_options, positional_options, subcommands)


def collect_commands() -> list[Category]:
    """
    Returns a sorted list of all available commands.

    i.e.
        a...
        backups
        backups create
        backups list
        backups restore
        c...

    Commands are sorted alphabetically and kept in groups.

    """
    parser = create_parser()

    result: list[Category] = []

    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            subparsers: dict[str, argparse.ArgumentParser] = action.choices
            for name, subparser in subparsers.items():
                if str(subparser.description).startswith("WIP"):
                    print(f"Excluded {name} from documentation as it is marked as WIP")
                    continue
                (_options, _positionals, _subcommands) = get_subcommands(
                    subparser, to=result, level=2, prefix=[name]
                )
                result.append(
                    Category(
                        title=name,
                        description=subparser.description,
                        options=_options,
                        positionals=_positionals,
                        subcommands=_subcommands,
                        epilog=subparser.epilog,
                        level=1,
                    )
                )

    def weight_cmd_groups(c: Category) -> tuple[str, str, int]:
        sub = [o for o in result if o.title.startswith(c.title) and o.title != c.title]
        weight = 10 - len(c.title.split(" "))
        if sub:
            weight = 10 - len(sub[0].title.split(" "))

        # 1. Sort by toplevel name alphabetically
        # 2. sort by custom weight to keep groups together
        # 3. sort by title alphabetically
        return (c.title.split(" ")[0], c.title, weight)

    result = sorted(result, key=weight_cmd_groups)

    return result


def build_command_reference() -> None:
    """
    Function that will build the reference
    and write it to the out path.
    """
    cmds = collect_commands()

    folder = Path("out")
    folder.mkdir(parents=True, exist_ok=True)

    # Index file
    markdown = "# CLI Overview\n\n"
    categories_fmt = ""
    for cat in cmds:
        categories_fmt += f"{cat.to_md_li()}\n\n" if cat.to_md_li() else ""

    if categories_fmt:
        markdown += """## Overview\n\n"""
        markdown += '<div class="grid cards" markdown>\n\n'
        markdown += categories_fmt
        markdown += "</div>"
        markdown += "\n"

    with (folder / "index.md").open("w") as f:
        f.write(markdown)

    # Each top level category is a separate file
    files: dict[Path, str] = {}

    for t in [cmd.title for cmd in cmds]:
        print(t)

    for cmd in cmds:
        # Collect all commands starting with the same name into one file
        filename = cmd.title.split(" ")[0]
        markdown = files.get(folder / f"{filename}.md", "")

        markdown += f"{'#'*(cmd.level)} {cmd.title.capitalize()}\n\n"

        markdown += f"{cmd.description}\n\n" if cmd.description else ""

        # usage: clan vms run [-h] machine
        markdown += f"""Usage: `clan {cmd.title}`\n\n"""

        # options:
        #   -h, --help  show this help message and exit

        # Positional arguments
        positionals_fmt = ""
        for option in cmd.positionals:
            positionals_fmt += f"""{option.to_md_li("1.")}\n"""

        if len(cmd.positionals):
            markdown += """!!! info "Positional arguments"\n"""
            markdown += indent_all(positionals_fmt)
            markdown += "\n"

        options_fmt = ""
        for option in cmd.options:
            options_fmt += f"{option.to_md_li()}\n"

        # options:
        if len(cmd.options):
            markdown += """??? info "Options"\n"""
            markdown += indent_all(options_fmt)
            markdown += "\n"

        def asort(s: Subcommand) -> str:
            return s.name

        commands_fmt = ""
        for sub_cmd in sorted(cmd.subcommands, key=asort):
            commands_fmt += f"{sub_cmd.to_md_li(cmd)}\n"

        if commands_fmt:
            markdown += """!!! info "Commands"\n"""
            markdown += indent_all(commands_fmt)
            markdown += "\n"

        markdown += f"{epilog_to_md(cmd.epilog)}\n\n" if cmd.epilog else ""

        files[folder / f"{filename}.md"] = markdown

    for fname, content in files.items():
        with fname.open("w") as f:
            f.write(content)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python docs.py <command>")
        print("Available commands: reference")
        sys.exit(1)

    command = sys.argv[1]

    if command == "reference":
        build_command_reference()


if __name__ == "__main__":
    main()
