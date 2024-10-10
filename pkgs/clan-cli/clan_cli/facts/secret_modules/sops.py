from pathlib import Path

from clan_cli.machines.machines import Machine
from clan_cli.secrets.folders import sops_secrets_folder
from clan_cli.secrets.machines import add_machine, has_machine
from clan_cli.secrets.secrets import decrypt_secret, encrypt_secret, has_secret
from clan_cli.secrets.sops import generate_private_key

from . import SecretStoreBase


class SecretStore(SecretStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine

        # no need to generate keys if we don't manage secrets
        if not hasattr(self.machine, "facts_data"):
            return

        if not self.machine.facts_data:
            return

        if has_machine(self.machine.flake_dir, self.machine.name):
            return
        priv_key, pub_key = generate_private_key()
        encrypt_secret(
            self.machine.flake_dir,
            sops_secrets_folder(self.machine.flake_dir)
            / f"{self.machine.name}-age.key",
            priv_key,
            add_groups=self.machine.deployment["sops"]["defaultGroups"],
        )
        add_machine(self.machine.flake_dir, self.machine.name, pub_key, False)

    def set(
        self, service: str, name: str, value: bytes, groups: list[str]
    ) -> Path | None:
        path = (
            sops_secrets_folder(self.machine.flake_dir) / f"{self.machine.name}-{name}"
        )
        encrypt_secret(
            self.machine.flake_dir,
            path,
            value,
            add_machines=[self.machine.name],
            add_groups=groups,
        )
        return path

    def get(self, service: str, name: str) -> bytes:
        return decrypt_secret(
            self.machine.flake_dir,
            sops_secrets_folder(self.machine.flake_dir) / f"{self.machine.name}-{name}",
        ).encode("utf-8")

    def exists(self, service: str, name: str) -> bool:
        return has_secret(
            sops_secrets_folder(self.machine.flake_dir) / f"{self.machine.name}-{name}",
        )

    def upload(self, output_dir: Path) -> None:
        key_name = f"{self.machine.name}-age.key"
        if not has_secret(sops_secrets_folder(self.machine.flake_dir) / key_name):
            # skip uploading the secret, not managed by us
            return
        key = decrypt_secret(
            self.machine.flake_dir,
            sops_secrets_folder(self.machine.flake_dir) / key_name,
        )
        (output_dir / "key.txt").write_text(key)
