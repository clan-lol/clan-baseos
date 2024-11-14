import subprocess
from pathlib import Path

import pytest
from clan_cli.clan_uri import FlakeId
from clan_cli.facts.secret_modules.password_store import SecretStore
from clan_cli.machines.facts import machine_get_fact
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.ssh import HostGroup
from fixtures_flakes import generate_flake
from helpers import cli
from helpers.nixos_config import nested_dict
from helpers.validator import is_valid_ssh_key
from root import CLAN_CORE


@pytest.mark.impure
def test_upload_secret(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    host_group: HostGroup,
) -> None:
    config = nested_dict()
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    # clan.core.networking.zerotier.controller.enable = true;
    config["clan"]["core"]["networking"]["zerotier"]["controller"]["enable"] = True
    host = host_group.hosts[0]
    addr = f"{host.user}@{host.host}:{host.port}?StrictHostKeyChecking=no&UserKnownHostsFile=/dev/null&IdentityFile={host.key}"
    config["clan"]["core"]["networking"]["targetHost"] = addr
    config["clan"]["user-password"]["user"] = "alice"
    config["clan"]["user-password"]["prompt"] = False
    facts = config["clan"]["core"]["facts"]
    facts["secretStore"] = "password-store"
    facts["secretUploadDirectory"]["_type"] = "override"
    facts["secretUploadDirectory"]["content"] = str(
        temporary_home / "flake" / "secrets"
    )
    facts["secretUploadDirectory"]["priority"] = 50

    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        monkeypatch=monkeypatch,
        machine_configs={"vm1": config},
        clan_modules=[
            "root-password",
            "user-password",
            "sshd",
        ],
    )
    monkeypatch.chdir(flake.path)
    gnupghome = temporary_home / "gpg"
    gnupghome.mkdir(mode=0o700)
    monkeypatch.setenv("GNUPGHOME", str(gnupghome))
    monkeypatch.setenv("PASSWORD_STORE_DIR", str(temporary_home / "pass"))
    gpg_key_spec = temporary_home / "gpg_key_spec"
    gpg_key_spec.write_text(
        """
        Key-Type: 1
        Key-Length: 1024
        Name-Real: Root Superuser
        Name-Email: test@local
        Expire-Date: 0
        %no-protection
    """
    )
    subprocess.run(
        nix_shell(
            ["nixpkgs#gnupg"], ["gpg", "--batch", "--gen-key", str(gpg_key_spec)]
        ),
        check=True,
    )
    subprocess.run(
        nix_shell(["nixpkgs#pass"], ["pass", "init", "test@local"]), check=True
    )
    cli.run(["facts", "generate", "vm1", "--flake", str(flake.path)])

    store = SecretStore(Machine(name="vm1", flake=FlakeId(str(flake.path))))

    network_id = machine_get_fact(flake.path, "vm1", "zerotier-network-id")
    assert len(network_id) == 16
    identity_secret = (
        temporary_home / "pass" / "machines" / "vm1" / "zerotier-identity-secret.gpg"
    )
    secret1_mtime = identity_secret.lstat().st_mtime_ns

    # test idempotency
    cli.run(["facts", "generate", "vm1"])
    assert identity_secret.lstat().st_mtime_ns == secret1_mtime
    cli.run(["facts", "upload", "vm1"])
    zerotier_identity_secret = flake.path / "secrets" / "zerotier-identity-secret"
    assert zerotier_identity_secret.exists()
    assert store.exists("", "zerotier-identity-secret")

    assert store.exists("", "password")
    assert store.exists("", "password-hash")
    assert store.exists("", "user-password")
    assert store.exists("", "user-password-hash")
    assert store.exists("", "ssh.id_ed25519")
    assert store.exists("", "zerotier-identity-secret")

    # Assert that the ssh key is valid
    ssh_secret = store.get("", "ssh.id_ed25519").decode()
    ssh_pub = machine_get_fact(flake.path, "vm1", "ssh.id_ed25519.pub")
    assert is_valid_ssh_key(ssh_secret, ssh_pub)

    # Assert that root-password is valid
    pwd_secret = store.get("", "password").decode()
    assert pwd_secret.isprintable()
    assert pwd_secret.isascii()
    pwd_hash = store.get("", "password-hash").decode()
    assert pwd_hash.isprintable()
    assert pwd_hash.isascii()

    # Assert that user-password is valid
    pwd_secret = store.get("", "user-password").decode()
    assert pwd_secret.isprintable()
    assert pwd_secret.isascii()
    pwd_hash = store.get("", "user-password-hash").decode()
    assert pwd_hash.isprintable()
    assert pwd_hash.isascii()
