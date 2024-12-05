# Functions to test
from clan_cli.inventory import determine_writeability, patch, unmerge_lists


# --------- Patching tests ---------
def test_patch_nested() -> None:
    orig = {"a": 1, "b": {"a": 2.1, "b": 2.2}, "c": 3}

    patch(orig, "b.b", "foo")

    # Should only update the nested value
    assert orig == {"a": 1, "b": {"a": 2.1, "b": "foo"}, "c": 3}


def test_patch_nested_dict() -> None:
    orig = {"a": 1, "b": {"a": 2.1, "b": 2.2}, "c": 3}

    # This should update the whole "b" dict
    # Which also removes all other keys
    patch(orig, "b", {"b": "foo"})

    # Should only update the nested value
    assert orig == {"a": 1, "b": {"b": "foo"}, "c": 3}


def test_create_missing_paths() -> None:
    orig = {"a": 1}

    patch(orig, "b.c", "foo")

    # Should only update the nested value
    assert orig == {"a": 1, "b": {"c": "foo"}}

    orig = {}
    patch(orig, "a.b.c", "foo")

    assert orig == {"a": {"b": {"c": "foo"}}}


# --------- Write tests ---------
#


def test_write_simple() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
            "bar": {"__prio": 1000},  # <- writeable: mkDefault "foo.bar"
        },
    }

    default: dict = {"foo": {}}
    data: dict = {}
    res = determine_writeability(prios, default, data)

    assert res == {"writeable": {"foo", "foo.bar"}, "non_writeable": set({})}


def test_write_inherited() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
            "bar": {
                # Inherits prio from parent <- writeable: "foo.bar"
                "baz": {"__prio": 1000},  # <- writeable: "foo.bar.baz"
            },
        },
    }

    data: dict = {}
    res = determine_writeability(prios, {"foo": {"bar": {}}}, data)
    assert res == {
        "writeable": {"foo", "foo.bar", "foo.bar.baz"},
        "non_writeable": set(),
    }


def test_non_write_inherited() -> None:
    prios = {
        "foo": {
            "__prio": 50,  # <- non writeable: mkForce "foo" = {...}
            "bar": {
                # Inherits prio from parent <- non writeable
                "baz": {"__prio": 1000},  # <- non writeable: mkDefault "foo.bar.baz"
            },
        },
    }

    data: dict = {}
    res = determine_writeability(prios, {}, data)
    assert res == {
        "writeable": set(),
        "non_writeable": {"foo", "foo.bar", "foo.bar.baz"},
    }


def test_write_list() -> None:
    prios = {
        "foo": {
            "__prio": 100,
        },
    }

    data: dict = {}
    default: dict = {
        "foo": [
            "a",
            "b",
        ]  # <- writeable: because lists are merged. Filtering out nix-values comes later
    }
    res = determine_writeability(prios, default, data)
    assert res == {
        "writeable": {"foo"},
        "non_writeable": set(),
    }


def test_write_because_written() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
            "bar": {
                # Inherits prio from parent <- writeable
                "baz": {"__prio": 100},  # <- non writeable usually
                "foobar": {"__prio": 100},  # <- non writeable
            },
        },
    }

    # Given the following data. {}
    # Check that the non-writeable paths are correct.
    res = determine_writeability(prios, {"foo": {"bar": {}}}, {})
    assert res == {
        "writeable": {"foo", "foo.bar"},
        "non_writeable": {"foo.bar.baz", "foo.bar.foobar"},
    }

    data: dict = {
        "foo": {
            "bar": {
                "baz": "foo"  # <- written. Since we created the data, we know we can write to it
            }
        }
    }
    res = determine_writeability(prios, {}, data)
    assert res == {
        "writeable": {"foo", "foo.bar", "foo.bar.baz"},
        "non_writeable": {"foo.bar.foobar"},
    }


# --------- List unmerge tests ---------


def test_list_unmerge() -> None:
    all_machines = ["machineA", "machineB"]
    inventory = ["machineB"]

    nix_machines = unmerge_lists(inventory, all_machines)
    assert nix_machines == ["machineA"]
