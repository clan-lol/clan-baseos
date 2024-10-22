from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pytest

# Functions to test
from clan_cli.api import dataclass_to_dict, from_dict
from clan_cli.errors import ClanError
from clan_cli.machines import machines


def test_simple() -> None:
    @dataclass
    class Person:
        name: str

    person_dict = {
        "name": "John",
    }

    expected_person = Person(
        name="John",
    )

    assert from_dict(Person, person_dict) == expected_person


def test_nested() -> None:
    @dataclass
    class Age:
        value: str

    @dataclass
    class Person:
        name: str
        # deeply nested dataclasses
        home: Path | str | None
        age: Age
        age_list: list[Age]
        age_dict: dict[str, Age]
        # Optional field

    person_dict = {
        "name": "John",
        "age": {
            "value": "99",
        },
        "age_list": [{"value": "66"}, {"value": "77"}],
        "age_dict": {"now": {"value": "55"}, "max": {"value": "100"}},
        "home": "/home",
    }

    expected_person = Person(
        name="John",
        age=Age("99"),
        age_list=[Age("66"), Age("77")],
        age_dict={"now": Age("55"), "max": Age("100")},
        home=Path("/home"),
    )

    assert from_dict(Person, person_dict) == expected_person


def test_nested_nullable() -> None:
    @dataclass
    class SystemConfig:
        language: str | None = field(default=None)
        keymap: str | None = field(default=None)
        ssh_keys_path: list[str] | None = field(default=None)

    @dataclass
    class FlashOptions:
        machine: machines.Machine
        mode: str
        disks: dict[str, str]
        system_config: SystemConfig
        dry_run: bool
        write_efi_boot_entries: bool
        debug: bool

    data = {
        "machine": {
            "name": "flash-installer",
            "flake": {"loc": "git+https://git.clan.lol/clan/clan-core"},
        },
        "mode": "format",
        "disks": {"main": "/dev/sda"},
        "system_config": {"language": "en_US.UTF-8", "keymap": "en"},
        "dry_run": False,
        "write_efi_boot_entries": False,
        "debug": False,
        "op_key": "jWnTSHwYhSgr7Qz3u4ppD",
    }

    expected = FlashOptions(
        machine=machines.Machine(
            name="flash-installer",
            flake=machines.FlakeId("git+https://git.clan.lol/clan/clan-core"),
        ),
        mode="format",
        disks={"main": "/dev/sda"},
        system_config=SystemConfig(
            language="en_US.UTF-8", keymap="en", ssh_keys_path=None
        ),
        dry_run=False,
        write_efi_boot_entries=False,
        debug=False,
    )

    assert from_dict(FlashOptions, data) == expected


def test_simple_field_missing() -> None:
    @dataclass
    class Person:
        name: str

    person_dict: Any = {}

    with pytest.raises(ClanError):
        from_dict(Person, person_dict)


def test_nullable() -> None:
    @dataclass
    class Person:
        name: None

    person_dict = {
        "name": None,
    }

    from_dict(Person, person_dict)


def test_nullable_non_exist() -> None:
    @dataclass
    class Person:
        name: None

    person_dict: Any = {}

    with pytest.raises(ClanError):
        from_dict(Person, person_dict)


def test_list() -> None:
    data = [
        {"name": "John"},
        {"name": "Sarah"},
    ]

    @dataclass
    class Name:
        name: str

    result = from_dict(list[Name], data)

    assert result == [Name("John"), Name("Sarah")]


def test_alias_field() -> None:
    @dataclass
    class Person:
        name: str = field(metadata={"alias": "--user-name--"})

    data = {"--user-name--": "John"}
    expected = Person(name="John")

    person = from_dict(Person, data)

    # Deserialize
    assert person == expected

    # Serialize with alias
    assert dataclass_to_dict(person) == data

    # Serialize without alias
    assert dataclass_to_dict(person, use_alias=False) == {"name": "John"}


def test_alias_field_from_orig_name() -> None:
    """
    Field declares an alias. But the data is provided with the field name.
    """

    @dataclass
    class Person:
        name: str = field(metadata={"alias": "--user-name--"})

    data = {"user": "John"}

    with pytest.raises(ClanError):
        from_dict(Person, data)


def test_none_or_string() -> None:
    """
    Field declares an alias. But the data is provided with the field name.
    """

    data = None

    @dataclass
    class Person:
        name: Path

    checked: str | None = from_dict(str | None, data)
    assert checked is None

    checked2: dict[str, str] | None = from_dict(dict[str, str] | None, data)
    assert checked2 is None

    checked3: Person | None = from_dict(Person | None, data)
    assert checked3 is None


def test_roundtrip_escape() -> None:
    assert from_dict(str, "\n") == "\n"
    assert dataclass_to_dict("\n") == "\n"

    # Test that the functions are inverses of each other
    # f(g(x)) == x
    # and
    # g(f(x)) == x
    assert from_dict(str, dataclass_to_dict("\n")) == "\n"
    assert dataclass_to_dict(from_dict(str, "\\n")) == "\\n"


def test_path_field() -> None:
    @dataclass
    class Person:
        name: Path

    data = {"name": "John"}
    expected = Person(name=Path("John"))

    assert from_dict(Person, data) == expected


def test_private_public_fields() -> None:
    @dataclass
    class Person:
        name: Path
        _name: str | None = None

    data = {"name": "John"}
    expected = Person(name=Path("John"))
    assert from_dict(Person, data) == expected

    assert dataclass_to_dict(expected) == data


def test_literal_field() -> None:
    @dataclass
    class Person:
        name: Literal["open_file", "select_folder", "save"]

    data = {"name": "open_file"}
    expected = Person(name="open_file")
    assert from_dict(Person, data) == expected

    assert dataclass_to_dict(expected) == data

    with pytest.raises(ClanError):
        # Not a valid value
        from_dict(Person, {"name": "open"})
