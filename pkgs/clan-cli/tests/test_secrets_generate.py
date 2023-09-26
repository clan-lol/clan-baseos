from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from cli import Cli

from clan_cli.machines.facts import machine_get_fact
from clan_cli.secrets.folders import sops_secrets_folder
from clan_cli.secrets.secrets import has_secret

if TYPE_CHECKING:
    from age_keys import KeyPair


@pytest.mark.impure
def test_upload_secret(
    monkeypatch: pytest.MonkeyPatch,
    test_flake_with_core: Path,
    age_keys: list["KeyPair"],
) -> None:
    monkeypatch.chdir(test_flake_with_core)
    monkeypatch.setenv("SOPS_AGE_KEY", age_keys[0].privkey)
    cli = Cli()
    cli.run(["secrets", "users", "add", "user1", age_keys[0].pubkey])
    cli.run(["secrets", "generate", "vm1"])
    has_secret("vm1-age.key")
    has_secret("vm1-zerotier-identity-secret")
    network_id = machine_get_fact("vm1", "zerotier-network-id")
    assert len(network_id) == 16
    age_key = sops_secrets_folder().joinpath("vm1-age.key").joinpath("secret")
    identity_secret = (
        sops_secrets_folder()
        .joinpath("vm1-zerotier-identity-secret")
        .joinpath("secret")
    )
    age_key_mtime = age_key.lstat().st_mtime_ns
    secret1_mtime = identity_secret.lstat().st_mtime_ns

    # test idempotency
    cli.run(["secrets", "generate", "vm1"])
    assert age_key.lstat().st_mtime_ns == age_key_mtime
    assert identity_secret.lstat().st_mtime_ns == secret1_mtime
