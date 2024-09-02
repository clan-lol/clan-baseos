import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import pytest
from clan_cli.errors import ClanError
from fixtures_flakes import FlakeForTest
from helpers import cli
from stdout import CaptureOutput

if TYPE_CHECKING:
    from age_keys import KeyPair

log = logging.getLogger(__name__)


def _test_identities(
    what: str,
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    age_keys: list["KeyPair"],
) -> None:
    sops_folder = test_flake.path / "sops"

    cli.run(
        [
            "secrets",
            what,
            "add",
            "--flake",
            str(test_flake.path),
            "foo",
            age_keys[0].pubkey,
        ]
    )
    assert (sops_folder / what / "foo" / "key.json").exists()

    with pytest.raises(ClanError):  # raises "foo already exists"
        cli.run(
            [
                "secrets",
                what,
                "add",
                "--flake",
                str(test_flake.path),
                "foo",
                age_keys[0].pubkey,
            ]
        )

    # rotate the key
    cli.run(
        [
            "secrets",
            what,
            "add",
            "--flake",
            str(test_flake.path),
            "-f",
            "foo",
            age_keys[1].privkey,
        ]
    )

    with capture_output as output:
        cli.run(
            [
                "secrets",
                what,
                "get",
                "--flake",
                str(test_flake.path),
                "foo",
            ]
        )
    assert age_keys[1].pubkey in output.out

    with capture_output as output:
        cli.run(["secrets", what, "list", "--flake", str(test_flake.path)])
    assert "foo" in output.out

    cli.run(["secrets", what, "remove", "--flake", str(test_flake.path), "foo"])
    assert not (sops_folder / what / "foo" / "key.json").exists()

    with pytest.raises(ClanError):  # already removed
        cli.run(["secrets", what, "remove", "--flake", str(test_flake.path), "foo"])

    with capture_output as output:
        cli.run(["secrets", what, "list", "--flake", str(test_flake.path)])
    assert "foo" not in output.out


def test_users(
    test_flake: FlakeForTest, capture_output: CaptureOutput, age_keys: list["KeyPair"]
) -> None:
    _test_identities("users", test_flake, capture_output, age_keys)


def test_machines(
    test_flake: FlakeForTest, capture_output: CaptureOutput, age_keys: list["KeyPair"]
) -> None:
    _test_identities("machines", test_flake, capture_output, age_keys)


def test_groups(
    test_flake: FlakeForTest, capture_output: CaptureOutput, age_keys: list["KeyPair"]
) -> None:
    with capture_output as output:
        cli.run(["secrets", "groups", "list", "--flake", str(test_flake.path)])
    assert output.out == ""

    with pytest.raises(ClanError):  # machine does not exist yet
        cli.run(
            [
                "secrets",
                "groups",
                "add-machine",
                "--flake",
                str(test_flake.path),
                "group1",
                "machine1",
            ]
        )
    with pytest.raises(ClanError):  # user does not exist yet
        cli.run(
            [
                "secrets",
                "groups",
                "add-user",
                "--flake",
                str(test_flake.path),
                "groupb1",
                "user1",
            ]
        )
    cli.run(
        [
            "secrets",
            "machines",
            "add",
            "--flake",
            str(test_flake.path),
            "machine1",
            age_keys[0].pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "add-machine",
            "--flake",
            str(test_flake.path),
            "group1",
            "machine1",
        ]
    )

    # Should this fail?
    cli.run(
        [
            "secrets",
            "groups",
            "add-machine",
            "--flake",
            str(test_flake.path),
            "group1",
            "machine1",
        ]
    )

    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake.path),
            "user1",
            age_keys[0].pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "add-user",
            "--flake",
            str(test_flake.path),
            "group1",
            "user1",
        ]
    )

    with capture_output as output:
        cli.run(["secrets", "groups", "list", "--flake", str(test_flake.path)])
    out = output.out
    assert "user1" in out
    assert "machine1" in out

    cli.run(
        [
            "secrets",
            "groups",
            "remove-user",
            "--flake",
            str(test_flake.path),
            "group1",
            "user1",
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "remove-machine",
            "--flake",
            str(test_flake.path),
            "group1",
            "machine1",
        ]
    )
    groups = os.listdir(test_flake.path / "sops" / "groups")
    assert len(groups) == 0


@contextmanager
def use_key(key: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    old_key = os.environ["SOPS_AGE_KEY_FILE"]
    monkeypatch.delenv("SOPS_AGE_KEY_FILE")
    monkeypatch.setenv("SOPS_AGE_KEY", key)
    try:
        yield
    finally:
        monkeypatch.delenv("SOPS_AGE_KEY")
        monkeypatch.setenv("SOPS_AGE_KEY_FILE", old_key)


def test_secrets(
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    monkeypatch: pytest.MonkeyPatch,
    age_keys: list["KeyPair"],
) -> None:
    with capture_output as output:
        cli.run(["secrets", "list", "--flake", str(test_flake.path)])
    assert output.out == ""

    monkeypatch.setenv("SOPS_NIX_SECRET", "foo")
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(test_flake.path / ".." / "age.key"))
    cli.run(["secrets", "key", "generate", "--flake", str(test_flake.path)])
    with capture_output as output:
        cli.run(["secrets", "key", "show", "--flake", str(test_flake.path)])
    key = output.out
    assert key.startswith("age1")
    cli.run(
        ["secrets", "users", "add", "--flake", str(test_flake.path), "testuser", key]
    )

    with pytest.raises(ClanError):  # does not exist yet
        cli.run(["secrets", "get", "--flake", str(test_flake.path), "nonexisting"])
    cli.run(["secrets", "set", "--flake", str(test_flake.path), "initialkey"])
    with capture_output as output:
        cli.run(["secrets", "get", "--flake", str(test_flake.path), "initialkey"])
    assert output.out == "foo"
    with capture_output as output:
        cli.run(["secrets", "users", "list", "--flake", str(test_flake.path)])
    users = output.out.rstrip().split("\n")
    assert len(users) == 1, f"users: {users}"
    owner = users[0]

    monkeypatch.setenv("EDITOR", "cat")
    cli.run(["secrets", "set", "--edit", "--flake", str(test_flake.path), "initialkey"])
    monkeypatch.delenv("EDITOR")

    cli.run(["secrets", "rename", "--flake", str(test_flake.path), "initialkey", "key"])

    with capture_output as output:
        cli.run(["secrets", "list", "--flake", str(test_flake.path)])
    assert output.out == "key\n"

    with capture_output as output:
        cli.run(["secrets", "list", "--flake", str(test_flake.path), "nonexisting"])
    assert output.out == ""

    with capture_output as output:
        cli.run(["secrets", "list", "--flake", str(test_flake.path), "key"])
    assert output.out == "key\n"

    cli.run(
        [
            "secrets",
            "machines",
            "add",
            "--flake",
            str(test_flake.path),
            "machine1",
            age_keys[1].pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "machines",
            "add-secret",
            "--flake",
            str(test_flake.path),
            "machine1",
            "key",
        ]
    )
    with capture_output as output:
        cli.run(["secrets", "machines", "list", "--flake", str(test_flake.path)])
    assert output.out == "machine1\n"

    with use_key(age_keys[1].privkey, monkeypatch):
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
        assert output.out == "foo"

    # rotate machines key
    cli.run(
        [
            "secrets",
            "machines",
            "add",
            "--flake",
            str(test_flake.path),
            "-f",
            "machine1",
            age_keys[0].privkey,
        ]
    )

    # should also rotate the encrypted secret
    with use_key(age_keys[0].privkey, monkeypatch):
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
        assert output.out == "foo"

    cli.run(
        [
            "secrets",
            "machines",
            "remove-secret",
            "--flake",
            str(test_flake.path),
            "machine1",
            "key",
        ]
    )

    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake.path),
            "user1",
            age_keys[1].pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "users",
            "add-secret",
            "--flake",
            str(test_flake.path),
            "user1",
            "key",
        ]
    )
    with capture_output as output, use_key(age_keys[1].privkey, monkeypatch):
        cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
    assert output.out == "foo"
    cli.run(
        [
            "secrets",
            "users",
            "remove-secret",
            "--flake",
            str(test_flake.path),
            "user1",
            "key",
        ]
    )

    with pytest.raises(ClanError):  # does not exist yet
        cli.run(
            [
                "secrets",
                "groups",
                "add-secret",
                "--flake",
                str(test_flake.path),
                "admin-group",
                "key",
            ]
        )
    cli.run(
        [
            "secrets",
            "groups",
            "add-user",
            "--flake",
            str(test_flake.path),
            "admin-group",
            "user1",
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "add-user",
            "--flake",
            str(test_flake.path),
            "admin-group",
            owner,
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "add-secret",
            "--flake",
            str(test_flake.path),
            "admin-group",
            "key",
        ]
    )

    cli.run(
        [
            "secrets",
            "set",
            "--flake",
            str(test_flake.path),
            "--group",
            "admin-group",
            "key2",
        ]
    )

    with use_key(age_keys[1].privkey, monkeypatch):
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
        assert output.out == "foo"

    # extend group will update secrets
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake.path),
            "user2",
            age_keys[2].pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "add-user",
            "--flake",
            str(test_flake.path),
            "admin-group",
            "user2",
        ]
    )

    with use_key(age_keys[2].privkey, monkeypatch):  # user2
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
        assert output.out == "foo"

    cli.run(
        [
            "secrets",
            "groups",
            "remove-user",
            "--flake",
            str(test_flake.path),
            "admin-group",
            "user2",
        ]
    )
    with pytest.raises(ClanError), use_key(age_keys[2].privkey, monkeypatch):
        # user2 is not in the group anymore
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
        print(output.out)

    cli.run(
        [
            "secrets",
            "groups",
            "remove-secret",
            "--flake",
            str(test_flake.path),
            "admin-group",
            "key",
        ]
    )

    cli.run(["secrets", "remove", "--flake", str(test_flake.path), "key"])
    cli.run(["secrets", "remove", "--flake", str(test_flake.path), "key2"])

    with capture_output as output:
        cli.run(["secrets", "list", "--flake", str(test_flake.path)])
    assert output.out == ""
