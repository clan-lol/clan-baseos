import enum
import logging
import sys
from dataclasses import dataclass
from getpass import getpass
from typing import Any

log = logging.getLogger(__name__)

# This is for simulating user input in tests.
MOCK_PROMPT_RESPONSE: None = None


class PromptType(enum.Enum):
    LINE = "line"
    HIDDEN = "hidden"
    MULTILINE = "multiline"


@dataclass
class Prompt:
    name: str
    description: str
    prompt_type: PromptType

    persist: bool = False
    previous_value: str | None = None

    @classmethod
    def from_json(cls: type["Prompt"], data: dict[str, Any]) -> "Prompt":
        return cls(
            name=data["name"],
            description=data["description"],
            prompt_type=PromptType(data["type"]),
            persist=data.get("persist", data["persist"]),
            previous_value=data.get("previousValue"),
        )


def ask(
    ident: str,
    input_type: PromptType,
    label: str | None,
) -> str:
    text = f"Enter the value for {ident}:"
    if label:
        text = f"{label}"

    if MOCK_PROMPT_RESPONSE:
        return next(MOCK_PROMPT_RESPONSE)
    match input_type:
        case PromptType.LINE:
            result = input(f"{text}: ")
        case PromptType.MULTILINE:
            print(f"{text} (Finish with Ctrl-D): ")
            result = sys.stdin.read()
        case PromptType.HIDDEN:
            result = getpass(f"{text} (hidden): ")

    log.info("Input received. Processing...")
    return result
