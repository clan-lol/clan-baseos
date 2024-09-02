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
        if not self.machine.vars_generators:
            return
        has_secrets = False
        for generator in self.machine.vars_generators.values():
            if "files" in generator:
                for file in generator["files"].values():
                    if file["secret"]:
                        has_secrets = True
        if not has_secrets:
            return

        if has_machine(self.machine.flake_dir, self.machine.name):
            return
        priv_key, pub_key = generate_private_key()
        encrypt_secret(
            self.machine.flake_dir,
            sops_secrets_folder(self.machine.flake_dir)
            / f"{self.machine.name}-age.key",
            priv_key,
        )
        add_machine(self.machine.flake_dir, self.machine.name, pub_key, False)

    def secret_path(
        self, generator_name: str, secret_name: str, shared: bool = False
    ) -> Path:
        if shared:
            base_path = self.machine.flake_dir / "sops" / "vars" / "shared"
        else:
            base_path = (
                self.machine.flake_dir
                / "sops"
                / "vars"
                / "per-machine"
                / self.machine.name
            )
        return base_path / generator_name / secret_name

    def set(
        self,
        generator_name: str,
        name: str,
        value: bytes,
        groups: list[str],
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        path = self.secret_path(generator_name, name, shared)
        encrypt_secret(
            self.machine.flake_dir,
            path,
            value,
            add_machines=[self.machine.name],
            add_groups=groups,
            meta={
                "deploy": deployed,
            },
        )
        return path

    def get(self, generator_name: str, name: str, shared: bool = False) -> bytes:
        return decrypt_secret(
            self.machine.flake_dir, self.secret_path(generator_name, name, shared)
        ).encode("utf-8")

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        return has_secret(
            self.secret_path(generator_name, name, shared),
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
