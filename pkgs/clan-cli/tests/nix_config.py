import json
import subprocess
from dataclasses import dataclass

import pytest


@dataclass
class ConfigItem:
    aliases: list[str]
    defaultValue: bool  # noqa: N815
    description: str
    documentDefault: bool  # noqa: N815
    experimentalFeature: str  # noqa: N815
    value: str | bool | list[str] | dict[str, str]


@pytest.fixture(scope="session")
def nix_config() -> dict[str, ConfigItem]:
    proc = subprocess.run(
        ["nix", "config", "show", "--json"], check=True, stdout=subprocess.PIPE
    )
    data = json.loads(proc.stdout)
    return {name: ConfigItem(**c) for name, c in data.items()}
