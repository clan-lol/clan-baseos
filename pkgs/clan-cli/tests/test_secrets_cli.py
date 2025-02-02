import functools
import json
import logging
import os
import re
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from clan_cli.errors import ClanError
from clan_cli.secrets.folders import sops_secrets_folder
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sops_folder = test_flake.path / "sops"

    what_singular = what[:-1]
    test_secret_name = f"{what_singular}_secret"

    # fake some admin user that's different from the identity, we are going to
    # try to add/remove/update from the clan, this way we can check that keys
    # are properly updated on secrets when an identity changes.
    admin_age_key = age_keys[2]

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

    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake.path),
            "admin",
            admin_age_key.pubkey,
        ]
    )

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

    with monkeypatch.context():
        monkeypatch.setenv("SOPS_NIX_SECRET", "deadfeed")
        monkeypatch.setenv("SOPS_AGE_KEY", admin_age_key.privkey)
        cli.run(
            [
                "secrets",
                "set",
                "--flake",
                str(test_flake.path),
                f"--{what_singular}",
                "foo",
                test_secret_name,
            ]
        )
    assert_sops_file_recipients(
        test_flake.path,
        test_secret_name,
        expected_age_recipients_keypairs=[age_keys[0], admin_age_key],
    )

    with monkeypatch.context():
        monkeypatch.setenv("SOPS_AGE_KEY", admin_age_key.privkey)
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
    assert_sops_file_recipients(
        test_flake.path,
        test_secret_name,
        expected_age_recipients_keypairs=[age_keys[1], admin_age_key],
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

    if what == "machines":
        # lopter@(2025-02-02): Let's address #2659 first and then figure out
        # what we wanna do about secrets when a machine is deleted.
        return

    user_symlink = sops_folder / "secrets" / test_secret_name / what / "foo"
    err_msg = (
        f"Symlink to {what_singular} foo's key in secret "
        f"{test_secret_name} was not cleaned up after "
        f"{what_singular} foo was removed."
    )
    assert not user_symlink.exists(follow_symlinks=False), err_msg


def test_users(
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    age_keys: list["KeyPair"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _test_identities("users", test_flake, capture_output, age_keys, monkeypatch)


def test_machines(
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    age_keys: list["KeyPair"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _test_identities("machines", test_flake, capture_output, age_keys, monkeypatch)


def test_groups(
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    age_keys: list["KeyPair"],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with capture_output as output:
        cli.run(["secrets", "groups", "list", "--flake", str(test_flake.path)])
    assert output.out == ""

    machine1_age_key = age_keys[0]
    user1_age_key = age_keys[1]
    admin_age_key = age_keys[2]

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
            machine1_age_key.pubkey,
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
            user1_age_key.pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake.path),
            "admin",
            admin_age_key.pubkey,
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

    secret_name = "foo"

    with monkeypatch.context():
        monkeypatch.setenv("SOPS_NIX_SECRET", "deafbeef")
        monkeypatch.setenv("SOPS_AGE_KEY", admin_age_key.privkey)
        cli.run(
            [
                "secrets",
                "set",
                "--flake",
                str(test_flake.path),
                "--group",
                "group1",
                secret_name,
            ]
        )

    assert_sops_file_recipients(
        test_flake.path,
        secret_name,
        expected_age_recipients_keypairs=[
            machine1_age_key,
            user1_age_key,
            admin_age_key,
        ],
        err_msg=(
            f"The secret `{secret_name}` owned by group1 was not encrypted "
            f"with all members of the group."
        ),
    )

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
    assert_sops_file_recipients(
        test_flake.path,
        secret_name,
        expected_age_recipients_keypairs=[machine1_age_key, admin_age_key],
        err_msg=(
            f"The secret `{secret_name}` owned by group1 is still encrypted for "
            f"`user1` even though this user has been removed from the group."
        ),
    )

    # re-add the user to the group
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
    assert_sops_file_recipients(
        test_flake.path,
        secret_name,
        expected_age_recipients_keypairs=[
            machine1_age_key,
            user1_age_key,
            admin_age_key,
        ],
    )
    # and instead of removing the user from the group, remove the
    # user instead, it should also remove it from the group:
    cli.run(
        [
            "secrets",
            "users",
            "remove",
            "--flake",
            str(test_flake.path),
            "user1",
        ]
    )
    assert_sops_file_recipients(
        test_flake.path,
        secret_name,
        expected_age_recipients_keypairs=[machine1_age_key, admin_age_key],
        err_msg=(
            f"The secret `{secret_name}` owned by group1 is still encrypted "
            f"for `user1` even though this user has been deleted."
        ),
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
    assert_sops_file_recipients(
        test_flake.path,
        secret_name,
        expected_age_recipients_keypairs=[admin_age_key],
        err_msg=(
            f"The secret `{secret_name}` owned by group1 is still encrypted for "
            f"`machine1` even though this machine has been removed from the group."
        ),
    )

    groups = os.listdir(test_flake.path / "sops" / "groups")
    assert len(groups) == 0

    # Check if the symlink to the group was removed from our foo test secret:
    group_symlink = test_flake.path / "sops/secrets/foo/groups/group1"
    err_msg = (
        "Symlink to group1's key in foo secret "
        "was not cleaned up after group1 was removed"
    )
    assert not group_symlink.exists(follow_symlinks=False), err_msg


def assert_sops_file_recipients(
    flake_path: Path,
    secret_name: str,
    expected_age_recipients_keypairs: list["KeyPair"],
    err_msg: str | None = None,
) -> None:
    """Checks that the recipients of a SOPS file matches expectations.

    :param err_msg: in case of failure, if you gave an error message then it
       will be displayed, otherwise pytest will display the two different sets
       of recipients.
    """
    sops_file = sops_secrets_folder(flake_path) / secret_name / "secret"
    with sops_file.open("rb") as fp:
        sops_data = json.load(fp)
    age_recipients = {each["recipient"] for each in sops_data["sops"]["age"]}
    expected_age_recipients = {pair.pubkey for pair in expected_age_recipients_keypairs}
    if not err_msg:
        assert age_recipients == expected_age_recipients
        return
    assert age_recipients == expected_age_recipients, err_msg


@contextmanager
def use_age_key(key: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    old_key = os.environ["SOPS_AGE_KEY_FILE"]
    monkeypatch.delenv("SOPS_AGE_KEY_FILE")
    monkeypatch.setenv("SOPS_AGE_KEY", key)
    try:
        yield
    finally:
        monkeypatch.delenv("SOPS_AGE_KEY")
        monkeypatch.setenv("SOPS_AGE_KEY_FILE", old_key)


@contextmanager
def use_gpg_key(key: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    old_key_file = os.environ.get("SOPS_AGE_KEY_FILE")
    old_key = os.environ.get("SOPS_AGE_KEY")
    monkeypatch.delenv("SOPS_AGE_KEY_FILE", raising=False)
    monkeypatch.delenv("SOPS_AGE_KEY", raising=False)
    monkeypatch.setenv("SOPS_PGP_FP", key)
    try:
        yield
    finally:
        monkeypatch.delenv("SOPS_PGP_FP")
        if old_key_file is not None:
            monkeypatch.setenv("SOPS_AGE_KEY_FILE", old_key_file)
        if old_key is not None:
            monkeypatch.setenv("SOPS_AGE_KEY", old_key)


@pytest.fixture
def gpg_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> str:
    gpg_home = tmp_path / "gnupghome"
    gpg_home.mkdir(mode=0o700)

    gpg_environ = os.environ.copy()
    gpg_environ["GNUPGHOME"] = str(gpg_home)
    run = functools.partial(
        subprocess.run,
        encoding="utf-8",
        check=True,
        env=gpg_environ,
    )
    key_parameters = "\n".join(
        (
            "%no-protection",
            "%transient-key",
            "Key-Type: rsa",
            "Key-Usage: cert encrypt",
            "Name-Real: Foo Bar",
            "Name-Comment: Test user",
            "Name-Email: test@clan.lol",
            "%commit",
        )
    )
    run(["gpg", "--batch", "--quiet", "--generate-key"], input=key_parameters)
    details = run(["gpg", "--list-keys", "--with-colons"], capture_output=True)
    fingerprint = None
    for line in details.stdout.strip().split(os.linesep):
        if not line.startswith("fpr"):
            continue
        fingerprint = line.split(":")[9]
        break
    assert fingerprint is not None, "Could not generate test GPG key"
    log.info(f"Created GPG key under {gpg_home}")

    monkeypatch.setenv("GNUPGHOME", str(gpg_home))
    return fingerprint


def test_secrets(
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    monkeypatch: pytest.MonkeyPatch,
    gpg_key: str,
    age_keys: list["KeyPair"],
) -> None:
    with capture_output as output:
        cli.run(["secrets", "list", "--flake", str(test_flake.path)])
    assert output.out == ""

    # Generate a new key for the clan
    monkeypatch.setenv("SOPS_AGE_KEY_FILE", str(test_flake.path / ".." / "age.key"))
    with capture_output as output:
        cli.run(["secrets", "key", "generate", "--flake", str(test_flake.path)])
    assert "age private key" in output.out
    # Read the key that was generated
    with capture_output as output:
        cli.run(["secrets", "key", "show", "--flake", str(test_flake.path)])
    key = json.loads(output.out)["publickey"]
    assert key.startswith("age1")
    # Add testuser with the key that was generated for the clan
    cli.run(
        ["secrets", "users", "add", "--flake", str(test_flake.path), "testuser", key]
    )

    with pytest.raises(ClanError):  # does not exist yet
        cli.run(["secrets", "get", "--flake", str(test_flake.path), "nonexisting"])
    monkeypatch.setenv("SOPS_NIX_SECRET", "foo")
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

    # using the `age_keys` KeyPair, add a machine and rotate its key

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

    with use_age_key(age_keys[1].privkey, monkeypatch):
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
    with use_age_key(age_keys[0].privkey, monkeypatch):
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
    with capture_output as output, use_age_key(age_keys[1].privkey, monkeypatch):
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

    with use_age_key(age_keys[1].privkey, monkeypatch):
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "key"])
        assert output.out == "foo"

    # Add an user with a GPG key
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake.path),
            "--pgp-key",
            gpg_key,
            "user2",
        ]
    )

    # Extend group will update secrets
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

    with use_gpg_key(gpg_key, monkeypatch):  # user2
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
    with (
        pytest.raises(ClanError),
        use_gpg_key(gpg_key, monkeypatch),
        capture_output as output,
    ):
        # user2 is not in the group anymore
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


def test_secrets_key_generate_gpg(
    test_flake: FlakeForTest,
    capture_output: CaptureOutput,
    monkeypatch: pytest.MonkeyPatch,
    gpg_key: str,
) -> None:
    with use_gpg_key(gpg_key, monkeypatch):
        # Make sure clan secrets key generate recognizes
        # the PGP key and does nothing:
        with capture_output as output:
            cli.run(
                [
                    "secrets",
                    "key",
                    "generate",
                    "--flake",
                    str(test_flake.path),
                ]
            )
        assert "age private key" not in output.out
        assert re.match(r"PGP key.+is already set", output.out) is not None

        with capture_output as output:
            cli.run(["secrets", "key", "show", "--flake", str(test_flake.path)])
        key = json.loads(output.out)
        assert key["type"] == "pgp"
        assert key["publickey"] == gpg_key

        # Add testuser with the key that was (not) generated for the clan:
        cli.run(
            [
                "secrets",
                "users",
                "add",
                "--flake",
                str(test_flake.path),
                "--pgp-key",
                gpg_key,
                "testuser",
            ]
        )
        with capture_output as output:
            cli.run(
                [
                    "secrets",
                    "users",
                    "get",
                    "--flake",
                    str(test_flake.path),
                    "testuser",
                ]
            )
        key = json.loads(output.out)
        assert key["type"] == "pgp"
        assert key["publickey"] == gpg_key

        monkeypatch.setenv("SOPS_NIX_SECRET", "secret-value")
        cli.run(["secrets", "set", "--flake", str(test_flake.path), "secret-name"])
        with capture_output as output:
            cli.run(["secrets", "get", "--flake", str(test_flake.path), "secret-name"])
        assert output.out == "secret-value"
