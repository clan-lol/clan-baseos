import os
from pathlib import Path

import pytest
from helpers import cli


class KeyPair:
    def __init__(self, pubkey: str, privkey: str) -> None:
        self.pubkey = pubkey
        self.privkey = privkey


class SopsSetup:
    def __init__(self, keys: list[KeyPair]) -> None:
        self.keys = keys

    def init(self, flake_path: Path | None = None) -> None:
        if flake_path is None:
            flake_path = Path.cwd()
        self.user = os.environ.get("USER", "user")
        cli.run(
            [
                "vars",
                "keygen",
                "--flake",
                str(flake_path),
                "--user",
                self.user,
            ]
        )


KEYS = [
    KeyPair(
        "age1dhwqzkah943xzc34tc3dlmfayyevcmdmxzjezdgdy33euxwf59vsp3vk3c",
        "AGE-SECRET-KEY-1KF8E3SR3TTGL6M476SKF7EEMR4H9NF7ZWYSLJUAK8JX276JC7KUSSURKFK",
    ),
    KeyPair(
        "age14tva0txcrl0zes05x7gkx56qd6wd9q3nwecjac74xxzz4l47r44sv3fz62",
        "AGE-SECRET-KEY-1U5ENXZQAY62NC78Y2WC0SEGRRMAEEKH79EYY5TH4GPFWJKEAY0USZ6X7YQ",
    ),
    KeyPair(
        "age1dhuh9xtefhgpr2sjjf7gmp9q2pr37z92rv4wsadxuqdx48989g7qj552qp",
        "AGE-SECRET-KEY-169N3FT32VNYQ9WYJMLUSVTMA0TTZGVJF7YZWS8AHTWJ5RR9VGR7QCD8SKF",
    ),
]


@pytest.fixture
def age_keys() -> list[KeyPair]:
    """
    Root directory of the tests
    """
    return KEYS


@pytest.fixture
def sops_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> SopsSetup:
    """
    Root directory of the tests
    """
    monkeypatch.setenv("SOPS_AGE_KEY", KEYS[0].privkey)
    return SopsSetup(KEYS)
