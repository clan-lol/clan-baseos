import ipaddress
from typing import TYPE_CHECKING

import pytest
from clan_cli.clan_uri import FlakeId
from clan_cli.facts.secret_modules.sops import SecretStore
from clan_cli.machines.facts import machine_get_fact
from clan_cli.machines.machines import Machine
from clan_cli.secrets.folders import sops_secrets_folder
from fixtures_flakes import FlakeForTest
from helpers import cli
from helpers.validator import is_valid_age_key

if TYPE_CHECKING:
    from age_keys import KeyPair


@pytest.mark.impure
def test_generate_secret(
    monkeypatch: pytest.MonkeyPatch,
    test_flake_with_core: FlakeForTest,
    age_keys: list["KeyPair"],
) -> None:
    monkeypatch.chdir(test_flake_with_core.path)
    monkeypatch.setenv("SOPS_AGE_KEY", age_keys[0].privkey)
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake_with_core.path),
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
            str(test_flake_with_core.path),
            "admins",
            "user1",
        ]
    )
    cmd = ["facts", "generate", "--flake", str(test_flake_with_core.path), "vm1"]
    cli.run(cmd)
    store1 = SecretStore(
        Machine(name="vm1", flake=FlakeId(str(test_flake_with_core.path)))
    )

    assert store1.exists("", "age.key")
    assert store1.exists("", "zerotier-identity-secret")
    network_id = machine_get_fact(
        test_flake_with_core.path, "vm1", "zerotier-network-id"
    )
    assert len(network_id) == 16
    secrets_folder = sops_secrets_folder(test_flake_with_core.path)
    age_key = secrets_folder / "vm1-age.key" / "secret"
    identity_secret = secrets_folder / "vm1-zerotier-identity-secret" / "secret"
    age_key_mtime = age_key.lstat().st_mtime_ns
    secret1_mtime = identity_secret.lstat().st_mtime_ns

    # Assert that the age key is valid
    age_secret = store1.get("", "age.key").decode()
    assert age_secret.isprintable()
    assert is_valid_age_key(age_secret)

    # test idempotency for vm1 and also generate for vm2
    cli.run(["facts", "generate", "--flake", str(test_flake_with_core.path)])
    assert age_key.lstat().st_mtime_ns == age_key_mtime
    assert identity_secret.lstat().st_mtime_ns == secret1_mtime

    assert (
        secrets_folder / "vm1-zerotier-identity-secret" / "machines" / "vm1"
    ).exists()

    store2 = SecretStore(
        Machine(name="vm2", flake=FlakeId(str(test_flake_with_core.path)))
    )

    # Should not exist clan facts generate
    assert not store2.exists("", "password")
    assert not store2.exists("", "password-hash")
    # clan vars generate
    # TODO: Test vars
    # varsStore = VarsSecretStore(
    #     machine=Machine(name="vm2", flake=FlakeId(str(test_flake_with_core.path)))
    # )
    # generators = get_generators(str(test_flake_with_core.path), "vm2")
    # generator = next((gen for gen in generators if gen.name == "root-password"), None)

    # if not generator:
    #     raise Exception("Generator not found")

    # password_update = GeneratorUpdate(
    #     generator=generator.name, prompt_values={"password": "1234"}
    # )
    # set_prompts(str(test_flake_with_core.path), "vm2", [password_update])
    # assert varsStore.exists(generator, "root-password")

    assert store2.exists("", "user-password")
    assert store2.exists("", "user-password-hash")
    assert store2.exists("", "age.key")
    assert store2.exists("", "zerotier-identity-secret")

    ip = machine_get_fact(test_flake_with_core.path, "vm1", "zerotier-ip")
    assert ipaddress.IPv6Address(ip).is_private

    # Assert that the age key is valid
    age_secret = store2.get("", "age.key").decode()
    assert age_secret.isprintable()
    assert is_valid_age_key(age_secret)

    # Assert that user-password is valid
    pwd_secret = store2.get("", "user-password").decode()
    assert pwd_secret.isprintable()
    assert pwd_secret.isascii()
    pwd_hash = store2.get("", "user-password-hash").decode()
    assert pwd_hash.isprintable()
    assert pwd_hash.isascii()
