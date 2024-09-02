from pathlib import Path

import pytest

from clan_cli import config
from clan_cli.config import parsing
from clan_cli.errors import ClanError

example_options = f"{Path(config.__file__).parent}/jsonschema/options.json"


def test_walk_jsonschema_all_types() -> None:
    schema = {
        "type": "object",
        "properties": {
            "array": {
                "type": "array",
                "items": {
                    "type": "string",
                },
            },
            "boolean": {"type": "boolean"},
            "integer": {"type": "integer"},
            "number": {"type": "number"},
            "string": {"type": "string"},
        },
    }
    expected = {
        "array": list[str],
        "boolean": bool,
        "integer": int,
        "number": float,
        "string": str,
    }
    assert config.parsing.options_types_from_schema(schema) == expected


def test_walk_jsonschema_nested() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "object",
                "properties": {
                    "first": {"type": "string"},
                    "last": {"type": "string"},
                },
            },
            "age": {"type": "integer"},
        },
    }
    expected = {
        "age": int,
        "name.first": str,
        "name.last": str,
    }
    assert config.parsing.options_types_from_schema(schema) == expected


# test walk_jsonschema with dynamic attributes (e.g. "additionalProperties")
def test_walk_jsonschema_dynamic_attrs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
            "users": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
        },
    }
    expected = {
        "age": int,
        "users.<name>": str,  # <name> is a placeholder for any string
    }
    assert config.parsing.options_types_from_schema(schema) == expected


def test_type_from_schema_path_simple() -> None:
    schema = {
        "type": "boolean",
    }
    assert parsing.type_from_schema_path(schema, []) is bool


def test_type_from_schema_path_nested() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "object",
                "properties": {
                    "first": {"type": "string"},
                    "last": {"type": "string"},
                },
            },
            "age": {"type": "integer"},
        },
    }
    assert parsing.type_from_schema_path(schema, ["age"]) is int
    assert parsing.type_from_schema_path(schema, ["name", "first"]) is str


def test_type_from_schema_path_dynamic_attrs() -> None:
    schema = {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
            "users": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
        },
    }
    assert parsing.type_from_schema_path(schema, ["age"]) is int
    assert parsing.type_from_schema_path(schema, ["users", "foo"]) is str


def test_map_type() -> None:
    with pytest.raises(ClanError):
        config.map_type("foo")
    assert config.map_type("string") is str
    assert config.map_type("integer") is int
    assert config.map_type("boolean") is bool
    assert config.map_type("attribute set of string") == dict[str, str]
    assert config.map_type("attribute set of integer") == dict[str, int]
    assert config.map_type("null or string") == str | None


# test the cast function with simple types
def test_cast() -> None:
    assert (
        config.cast(value=["true"], input_type=bool, opt_description="foo-option")
        is True
    )
    assert (
        config.cast(value=["null"], input_type=str | None, opt_description="foo-option")
        is None
    )
    assert (
        config.cast(value=["bar"], input_type=str | None, opt_description="foo-option")
        == "bar"
    )


@pytest.mark.parametrize(
    "option,value,options,expected",
    [
        ("foo.bar", ["baz"], {"foo.bar": {"type": "str"}}, ("foo.bar", ["baz"])),
        ("foo.bar", ["baz"], {"foo": {"type": "attrs"}}, ("foo", {"bar": ["baz"]})),
        (
            "users.users.my-user.name",
            ["my-name"],
            {"users.users.<name>.name": {"type": "str"}},
            ("users.users.<name>.name", ["my-name"]),
        ),
        (
            "foo.bar.baz.bum",
            ["val"],
            {"foo.<name>.baz": {"type": "attrs"}},
            ("foo.<name>.baz", {"bum": ["val"]}),
        ),
        (
            "userIds.DavHau",
            ["42"],
            {"userIds": {"type": "attrs"}},
            ("userIds", {"DavHau": ["42"]}),
        ),
    ],
)
def test_find_option(option: str, value: list, options: dict, expected: tuple) -> None:
    assert config.find_option(option, value, options) == expected
