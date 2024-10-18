from dataclasses import dataclass, field

# Functions to test
from clan_cli.api import (
    dataclass_to_dict,
    sanitize_string,
)


#
def test_sanitize_string() -> None:
    # Simple strings
    assert sanitize_string("Hello World") == "Hello World"
    assert sanitize_string("Hello\nWorld") == "Hello\nWorld"
    assert sanitize_string("Hello\tWorld") == "Hello\tWorld"
    assert sanitize_string("Hello\rWorld") == "Hello\rWorld"
    assert sanitize_string("Hello\fWorld") == "Hello\fWorld"
    assert sanitize_string("Hello\vWorld") == "Hello\u000bWorld"
    assert sanitize_string("Hello\bWorld") == "Hello\bWorld"
    assert sanitize_string("Hello\\World") == "Hello\\World"
    assert sanitize_string('Hello"World') == 'Hello"World'
    assert sanitize_string("Hello'World") == "Hello'World"
    assert sanitize_string("Hello\0World") == "Hello\x00World"
    # Console escape characters

    assert sanitize_string("\033[1mBold\033[0m") == "\033[1mBold\033[0m"  # Red
    assert sanitize_string("\033[31mRed\033[0m") == "\033[31mRed\033[0m"  # Blue
    assert sanitize_string("\033[42mGreen\033[0m") == "\033[42mGreen\033[0m"  # Green
    assert sanitize_string("\033[4mUnderline\033[0m") == "\033[4mUnderline\033[0m"
    assert (
        sanitize_string("\033[91m\033[1mBold Red\033[0m")
        == "\033[91m\033[1mBold Red\033[0m"
    )


def test_dataclass_to_dict() -> None:
    @dataclass
    class Person:
        name: str
        age: int

    person = Person(name="John", age=25)
    expected_dict = {"name": "John", "age": 25}
    assert dataclass_to_dict(person) == expected_dict


def test_dataclass_to_dict_nested() -> None:
    @dataclass
    class Address:
        city: str = "afghanistan"
        zip: str = "01234"

    @dataclass
    class Person:
        name: str
        age: int
        address: Address = field(default_factory=Address)

    person1 = Person(name="John", age=25)
    expected_dict1 = {
        "name": "John",
        "age": 25,
        "address": {"city": "afghanistan", "zip": "01234"},
    }
    # address must be constructed with default values if not passed
    assert dataclass_to_dict(person1) == expected_dict1

    person2 = Person(name="John", age=25, address=Address(zip="0", city="Anywhere"))
    expected_dict2 = {
        "name": "John",
        "age": 25,
        "address": {"zip": "0", "city": "Anywhere"},
    }
    assert dataclass_to_dict(person2) == expected_dict2


def test_dataclass_to_dict_defaults() -> None:
    @dataclass
    class Foo:
        home: dict[str, str] = field(default_factory=dict)
        work: list[str] = field(default_factory=list)

    @dataclass
    class Person:
        name: str = field(default="jon")
        age: int = field(default=1)
        foo: Foo = field(default_factory=Foo)

    default_person = Person()
    expected_default = {
        "name": "jon",
        "age": 1,
        "foo": {"home": {}, "work": []},
    }
    # address must be constructed with default values if not passed
    assert dataclass_to_dict(default_person) == expected_default

    real_person = Person(name="John", age=25, foo=Foo(home={"a": "b"}, work=["a", "b"]))
    expected = {
        "name": "John",
        "age": 25,
        "foo": {"home": {"a": "b"}, "work": ["a", "b"]},
    }
    assert dataclass_to_dict(real_person) == expected


def test_filters_null_fields() -> None:
    @dataclass
    class Foo:
        home: str | None = None
        work: str | None = None

    # None fields are filtered out
    instance = Foo()

    assert instance.home is None
    assert dataclass_to_dict(instance) == {}

    # fields that are set are not filtered
    instance = Foo(home="home")

    assert instance.home == "home"
    assert instance.work is None
    assert dataclass_to_dict(instance) == {"home": "home"}
