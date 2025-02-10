# Functions to test
from typing import Any

import pytest
from clan_cli.errors import ClanError
from clan_cli.inventory import (
    calc_patches,
    delete_by_path,
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
    patchset, _ = calc_patches(
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
    patchset, _ = calc_patches(
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
    update = {"foo": ["A", "B", "C"]}  # User wants to add "C"

    patchset, _ = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {"foo": ["B", "C"]}

    # "foo": ["A", "B"]
    # Remove "B" from the list
    # Expected is [ ] because ["A"] is defined in nix
    update = {"foo": ["A"]}  # User wants to remove "B"

    patchset, _ = calc_patches(
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
    update = {"foo": ["A", "B", "A"]}  # User wants to add duplicate "A"

    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update, all_values=data_eval, writeables=writeables)

    assert (
        str(error.value)
        == "Key 'foo' contains duplicates: ['A']. This not supported yet."
    )


def test_dont_persist_defaults() -> None:
    """
    Default values should not be persisted to disk if not explicitly requested by the user.
    """

    prios = {
        "enabled": {"__prio": 1500},
        "config": {"__prio": 100},
    }
    data_eval = {
        "enabled": True,
        "config": {"foo": "bar"},
    }
    data_disk: dict[str, Any] = {}
    writeables = determine_writeability(prios, data_eval, data_disk)
    assert writeables == {"writeable": {"config", "enabled"}, "non_writeable": set()}

    update = {"config": {"foo": "foo"}}
    patchset, delete_set = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )
    assert patchset == {"config.foo": "foo"}
    assert delete_set == set()


def test_machine_delete() -> None:
    prios = {
        "machines": {"__prio": 100},
    }
    data_eval = {
        "machines": {
            "foo": {"name": "foo"},
            "bar": {"name": "bar"},
            "naz": {"name": "naz"},
        },
    }
    data_disk = data_eval

    writeables = determine_writeability(prios, data_eval, data_disk)
    assert writeables == {"writeable": {"machines"}, "non_writeable": set()}

    # Delete machine "bar"  from the inventory
    update = {"machines": {"foo": {"name": "foo"}, "naz": {"name": "naz"}}}
    patchset, delete_set = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {}
    assert delete_set == {"machines.bar"}


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

    # set foo to an int but it is a list
    update: dict = {"foo": 1}

    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update, all_values=data_eval, writeables=writeables)

    assert (
        str(error.value)
        == "Type mismatch for key 'foo'. Cannot update <class 'list'> with <class 'int'>"
    )


def test_delete_key() -> None:
    prios = {
        "foo": {
            "__prio": 100,  # <- writeable: "foo"
        },
    }

    data_eval = {"foo": {"bar": "baz"}}

    data_disk = data_eval

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": {"foo"}, "non_writeable": set()}

    # remove all keys from foo
    update: dict = {"foo": {}}

    patchset, delete_set = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {}
    assert delete_set == {"foo.bar"}


def test_delete_key_intermediate() -> None:
    prios = {
        "foo": {
            "__prio": 100,
        },
    }

    data_eval = {
        "foo": {
            # Remove the key "bar"
            "bar": {"name": "bar", "info": "info", "other": ["a", "b"]},
            # Leave the key "other"
            "other": {"name": "other", "info": "info", "other": ["a", "b"]},
        }
    }
    update: dict = {
        "foo": {"other": {"name": "other", "info": "info", "other": ["a", "b"]}}
    }

    data_disk = data_eval

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": {"foo"}, "non_writeable": set()}

    # remove all keys from foo

    patchset, delete_set = calc_patches(
        data_disk, update, all_values=data_eval, writeables=writeables
    )

    assert patchset == {}
    assert delete_set == {"foo.bar"}


def test_delete_key_non_writeable() -> None:
    prios = {
        "foo": {
            "__prio": 50,
        },
    }

    data_eval = {
        "foo": {
            # Remove the key "bar"
            "bar": {"name": "bar", "info": "info", "other": ["a", "b"]},
        }
    }
    update: dict = {"foo": {}}

    data_disk = data_eval

    writeables = determine_writeability(prios, data_eval, data_disk)

    assert writeables == {"writeable": set(), "non_writeable": {"foo"}}

    # remove all keys from foo
    with pytest.raises(ClanError) as error:
        calc_patches(data_disk, update, all_values=data_eval, writeables=writeables)

    assert "Cannot delete" in str(error.value)


def test_delete_atom() -> None:
    data = {"foo": {"bar": 1}}
    # Removes the key "foo.bar"
    # Returns the deleted key-value pair { "bar": 1 }
    entry = delete_by_path(data, "foo.bar")

    assert entry == {"bar": 1}
    assert data == {"foo": {}}


def test_delete_intermediate() -> None:
    data = {"a": {"b": {"c": {"d": 42}}}}
    # Removes "a.b.c.d"
    entry = delete_by_path(data, "a.b.c")

    assert entry == {"c": {"d": 42}}
    # Check all intermediate dictionaries remain intact
    assert data == {"a": {"b": {}}}


def test_delete_top_level() -> None:
    data = {"x": 100, "y": 200}
    # Deletes top-level key
    entry = delete_by_path(data, "x")
    assert entry == {"x": 100}
    assert data == {"y": 200}


def test_delete_key_not_found() -> None:
    data = {"foo": {"bar": 1}}
    # Trying to delete a non-existing key "foo.baz"
    with pytest.raises(ClanError) as excinfo:
        delete_by_path(data, "foo.baz")
    assert "Cannot delete. Path 'foo.baz'" in str(excinfo.value)
    # Data should remain unchanged
    assert data == {"foo": {"bar": 1}}


def test_delete_intermediate_not_dict() -> None:
    data = {"foo": "not a dict"}
    # Trying to go deeper into a non-dict value
    with pytest.raises(ClanError) as excinfo:
        delete_by_path(data, "foo.bar")
    assert "not found or not a dictionary" in str(excinfo.value)
    # Data should remain unchanged
    assert data == {"foo": "not a dict"}


def test_delete_empty_path() -> None:
    data = {"foo": {"bar": 1}}
    # Attempting to delete with an empty path
    with pytest.raises(ClanError) as excinfo:
        delete_by_path(data, "")
    # Depending on how you handle empty paths, you might raise an error or handle it differently.
    # If you do raise an error, check the message.
    assert "Cannot delete. Path is empty" in str(excinfo.value)
    assert data == {"foo": {"bar": 1}}


def test_delete_non_existent_path_deep() -> None:
    data = {"foo": {"bar": {"baz": 123}}}
    # non-existent deep path
    with pytest.raises(ClanError) as excinfo:
        delete_by_path(data, "foo.bar.qux")
    assert "not found" in str(excinfo.value)
    # Data remains unchanged
    assert data == {"foo": {"bar": {"baz": 123}}}
