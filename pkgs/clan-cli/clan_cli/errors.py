import contextlib
import json
import os
import shlex
import shutil
from dataclasses import dataclass
from math import floor
from pathlib import Path
from typing import cast


def get_term_filler(name: str) -> tuple[int, int]:
    width, _ = shutil.get_terminal_size()

    filler = floor((width - len(name)) / 2)
    return (filler - 1, width)


def text_heading(heading: str) -> str:
    filler, total = get_term_filler(heading)
    msg = f"{'=' * filler} {heading} {'=' * filler}"
    if len(msg) < total:
        msg += "="
    return msg


def optional_text(heading: str, text: str | None) -> str:
    if text is None or text.strip() == "":
        return ""

    with contextlib.suppress(json.JSONDecodeError):
        text = json.dumps(json.loads(text), indent=4)

    return f"{text_heading(heading)}\n{text}"


@dataclass
class DictDiff:
    added: dict[str, str]
    removed: dict[str, str]
    changed: dict[str, dict[str, str]]


def diff_dicts(dict1: dict[str, str], dict2: dict[str, str]) -> DictDiff:
    """
    Compare two dictionaries and report additions, deletions, and changes.

    :param dict1: The first dictionary (baseline).
    :param dict2: The second dictionary (to compare).
    :return: A dictionary with keys 'added', 'removed', and 'changed', each containing
             the respective differences. 'changed' is a nested dictionary with keys 'old' and 'new'.
    """
    added = {k: dict2[k] for k in dict2 if k not in dict1}
    removed = {k: dict1[k] for k in dict1 if k not in dict2}
    changed = {
        k: {"old": dict1[k], "new": dict2[k]}
        for k in dict1
        if k in dict2 and dict1[k] != dict2[k]
    }

    return DictDiff(added=added, removed=removed, changed=changed)


def indent_command(command_list: list[str]) -> str:
    formatted_command = []
    i = 0
    while i < len(command_list):
        arg = command_list[i]
        formatted_command.append(shlex.quote(arg))

        if i < len(command_list) - 1:
            # Check if the current argument is an option
            if arg.startswith("-"):
                # Indent after the next argument
                formatted_command.append(" ")
                i += 1
                formatted_command.append(shlex.quote(command_list[i]))

        if i < len(command_list) - 1:
            # Add line continuation only if it's not the last argument
            formatted_command.append(" \\\n    ")

        i += 1

    # Join the list into a single string
    final_command = "".join(formatted_command)

    # Remove the trailing continuation if it exists
    if final_command.endswith(" \\ \n    "):
        final_command = final_command.rsplit(" \\ \n    ", 1)[0]
    return final_command


DEBUG_COMMANDS = os.environ.get("CLAN_DEBUG_COMMANDS", False)


@dataclass
class CmdOut:
    stdout: str
    stderr: str
    env: dict[str, str] | None
    cwd: Path
    command_list: list[str]
    returncode: int
    msg: str | None

    @property
    def command(self) -> str:
        return indent_command(self.command_list)

    def __str__(self) -> str:
        # Set a common indentation level, assuming a reasonable spacing
        label_width = max(len("Return Code"), len("Work Dir"), len("Error Msg"))
        error_msg = [
            f"""
{optional_text("Command", self.command)}
{optional_text("Stdout", self.stdout)}
{optional_text("Stderr", self.stderr)}
{'Return Code:':<{label_width}} {self.returncode}
"""
        ]
        if self.msg:
            error_msg += [f"{'Error Msg:':<{label_width}} {self.msg.capitalize()}"]

        if DEBUG_COMMANDS:
            diffed_dict = (
                diff_dicts(cast(dict[str, str], os.environ), self.env)
                if self.env
                else None
            )
            diffed_dict_str = (
                json.dumps(diffed_dict.__dict__, indent=4) if diffed_dict else None
            )
            error_msg += [
                f"""
{optional_text("Environment", diffed_dict_str)}
{text_heading(heading="Metadata")}
{'Work Dir:':<{label_width}} '{self.cwd}'
"""
            ]
        return "\n".join(error_msg)


class ClanError(Exception):
    """Base class for exceptions in this module."""

    description: str | None
    location: str

    def __init__(
        self,
        msg: str | None = None,
        *,
        description: str | None = None,
        location: str | None = None,
    ) -> None:
        self.description = description
        self.location = location or "Unknown location"
        self.msg = msg or ""
        exception_msg = ""
        if location:
            exception_msg += f"{location}: \n"
        exception_msg += self.msg

        if self.description:
            exception_msg += f" - {self.description}"
        super().__init__(exception_msg)


class ClanHttpError(ClanError):
    status_code: int
    msg: str

    def __init__(self, status_code: int, msg: str) -> None:
        self.status_code = status_code
        self.msg = msg
        super().__init__(msg)


class ClanCmdError(ClanError):
    cmd: CmdOut

    def __init__(self, cmd: CmdOut) -> None:
        self.cmd = cmd
        super().__init__()

    def __str__(self) -> str:
        return str(self.cmd)

    def __repr__(self) -> str:
        return f"ClanCmdError({self.cmd})"
