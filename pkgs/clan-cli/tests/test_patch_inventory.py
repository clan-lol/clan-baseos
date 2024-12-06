# Functions to test
import pytest
from clan_cli.errors import ClanError
from clan_cli.inventory import (
    calc_patches,
    determine_writeability,
    patch,
    unmerge_lists,
)


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

    nix_machines = unmerge_lists(all_machines, inventory)
    assert nix_machines == ["machineA"]


# --------- Write tests ---------


def test_update_simple() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
            "bar": {"__prio": 1000},  # <- writeable: mkDefault "foo.bar"
            "nix": {"__prio": 100},  # <- non writeable: "foo.bar" (defined in nix)
        },
    }

    data_eval = {"foo": {"bar": "baz", "nix": "this is set in nix"}}

    data_disk: dict = {}

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": {"foo", "foo.bar"}, "non_writeable": {"foo.nix"}}

    update = {
        "foo": {
            "bar": "new value",  # <- user sets this value
            "nix": "this is set in nix",  # <- user didnt touch this value
            # If the user would have set this value, it would trigger an error
        }
    }
    patchset = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {"foo.bar": "new value"}


def test_update_many() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
            "bar": {"__prio": 100},  # <-
            "nix": {"__prio": 100},  # <- non writeable: "foo.bar" (defined in nix)
            "nested": {
                "__prio": 100,
                "x": {"__prio": 100},  # <- writeable: "foo.nested.x"
                "y": {"__prio": 100},  # <- non-writeable: "foo.nested.y"
            },
        },
    }

    data_eval = {
        "foo": {
            "bar": "baz",
            "nix": "this is set in nix",
            "nested": {"x": "x", "y": "y"},
        }
    }

    data_disk = {"foo": {"bar": "baz", "nested": {"x": "x"}}}

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {
        "writeable": {"foo.nested", "foo", "foo.bar", "foo.nested.x"},
        "non_writeable": {"foo.nix", "foo.nested.y"},
    }

    update = {
        "foo": {
            "bar": "new value for bar",  # <- user sets this value
            "nix": "this is set in nix",  # <- user cannot set this value
            "nested": {
                "x": "new value for x",  # <- user sets this value
                "y": "y",  # <- user cannot set this value
            },
        }
    }
    patchset = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {
        "foo.bar": "new value for bar",
        "foo.nested.x": "new value for x",
    }


def test_update_parent_non_writeable() -> None:
    prios = {
        "foo": {
            "__prio": 50,  # <- non-writeable: "foo"
            "bar": {"__prio": 1000},  # <- writeable: mkDefault "foo.bar"
        },
    }

    data_eval = {
        "foo": {
            "bar": "baz",
        }
    }

    data_disk = {
        "foo": {
            "bar": "baz",
        }
    }

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": set(), "non_writeable": {"foo", "foo.bar"}}

    update = {
        "foo": {
            "bar": "new value",  # <- user sets this value
        }
    }
    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update, all_values=data_eval, writeables=writeables)

    assert str(error.value) == "Key 'foo.bar' is not writeable."


def test_update_list() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
        },
    }

    data_eval = {
        #  [ "A" ]  is defined in nix.
        "foo": ["A", "B"]
    }

    data_disk = {"foo": ["B"]}

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": {"foo"}, "non_writeable": set()}

    # Add "C" to the list
    update = {
        "foo": ["A", "B", "C"]  # User wants to add "C"
    }

    patchset = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {"foo": ["B", "C"]}

    # Remove "B" from the list
    update = {
        "foo": ["A"]  # User wants to remove "B"
    }

    patchset = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {"foo": []}


def test_update_list_duplicates() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
        },
    }

    data_eval = {
        #  [ "A" ]  is defined in nix.
        "foo": ["A", "B"]
    }

    data_disk = {"foo": ["B"]}

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": {"foo"}, "non_writeable": set()}

    # Add "A" to the list
    update = {
        "foo": ["A", "B", "A"]  # User wants to add duplicate "A"
    }

    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update, all_values=data_eval, writeables=writeables)

    assert (
        str(error.value)
        == "Key 'foo' contains duplicates: ['A']. This not supported yet."
    )


def test_update_mismatching_update_type() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
        },
    }

    data_eval = {"foo": ["A", "B"]}

    data_disk: dict = {}

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": {"foo"}, "non_writeable": set()}

    # set foo.A which doesnt exist
    update_1 = {"foo": {"A": "B"}}

    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update_1, all_values=data_eval, writeables=writeables)

    assert str(error.value) == "Key 'foo.A' cannot be set. It does not exist."

    # set foo to an int but it is a list
    update_2: dict = {"foo": 1}

    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update_2, all_values=data_eval, writeables=writeables)

    assert (
        str(error.value)
        == "Type mismatch for key 'foo'. Cannot update <class 'list'> with <class 'int'>"
    )
