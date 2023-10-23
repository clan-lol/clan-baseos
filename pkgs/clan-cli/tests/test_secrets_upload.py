from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from cli import Cli
from fixtures_flakes import FlakeForTest
from clan_cli.ssh import HostGroup

if TYPE_CHECKING:
    from age_keys import KeyPair


@pytest.mark.impure
def test_secrets_upload(
    monkeypatch: pytest.MonkeyPatch,
    test_flake_with_core: FlakeForTest,
    host_group: HostGroup,
    age_keys: list["KeyPair"],
) -> None:
    monkeypatch.chdir(test_flake_with_core.path)
    monkeypatch.setenv("SOPS_AGE_KEY", age_keys[0].privkey)

    cli = Cli()
    cli.run(["secrets", "users", "add", "user1", age_keys[0].pubkey, test_flake_with_core.name])

    cli.run(["secrets", "machines", "add", "vm1", age_keys[1].pubkey, test_flake_with_core.name])
    monkeypatch.setenv("SOPS_NIX_SECRET", age_keys[0].privkey)
    cli.run(["secrets", "set", "vm1-age.key", test_flake_with_core.name])

    flake = test_flake_with_core.path.joinpath("flake.nix")
    host = host_group.hosts[0]
    addr = f"{host.user}@{host.host}:{host.port}?StrictHostKeyChecking=no&UserKnownHostsFile=/dev/null&IdentityFile={host.key}"
    new_text = flake.read_text().replace("__CLAN_DEPLOYMENT_ADDRESS__", addr)

    flake.write_text(new_text)
    cli.run(["secrets", "upload", "vm1", test_flake_with_core.name])

    # the flake defines this path as the location where the sops key should be installed
    sops_key = test_flake_with_core.path.joinpath("key.txt")
    assert sops_key.exists()
    assert sops_key.read_text() == age_keys[0].privkey
