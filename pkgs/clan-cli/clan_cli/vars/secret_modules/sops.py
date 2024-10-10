import json
from dataclasses import dataclass
from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine
from clan_cli.secrets.folders import sops_machines_folder, sops_secrets_folder
from clan_cli.secrets.machines import add_machine, add_secret, has_machine
from clan_cli.secrets.secrets import decrypt_secret, encrypt_secret, has_secret
from clan_cli.secrets.sops import generate_private_key

from . import SecretStoreBase


@dataclass
class SopsKey:
    pubkey: str
    username: str


class MissingKeyError(ClanError):
    def __init__(self) -> None:
        msg = "Cannot find admin keys for current $USER on this computer. Please initialize admin keys once with 'clan vars keygen'"
        super().__init__(msg)


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
            add_groups=self.machine.deployment["sops"]["defaultGroups"],
        )
        add_machine(self.machine.flake_dir, self.machine.name, pub_key, False)

    @property
    def store_name(self) -> str:
        return "sops"

    def machine_has_access(
        self, generator_name: str, secret_name: str, shared: bool
    ) -> bool:
        secret_path = self.secret_path(generator_name, secret_name, shared)
        secret = json.loads((secret_path / "secret").read_text())
        recipients = [r["recipient"] for r in (secret["sops"].get("age") or [])]
        machines_folder_path = sops_machines_folder(self.machine.flake_dir)
        machine_pubkey = json.loads(
            (machines_folder_path / self.machine.name / "key.json").read_text()
        )["publickey"]
        return machine_pubkey in recipients

    def secret_path(
        self, generator_name: str, secret_name: str, shared: bool = False
    ) -> Path:
        return self.directory(generator_name, secret_name, shared=shared)

    def _set(
        self,
        generator_name: str,
        name: str,
        value: bytes,
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        secret_folder = self.secret_path(generator_name, name, shared)
        # delete directory
        if secret_folder.exists() and not (secret_folder / "secret").exists():
            # another backend has used that folder before -> error out
            self.backend_collision_error(secret_folder)
        # create directory if it doesn't exist
        secret_folder.mkdir(parents=True, exist_ok=True)
        if shared and self.exists_shared(generator_name, name):
            # secret exists, but this machine doesn't have access -> add machine
            # add_secret will be a no-op if the machine is already added
            add_secret(self.machine.flake_dir, self.machine.name, secret_folder)
        else:
            # initialize the secret
            encrypt_secret(
                self.machine.flake_dir,
                secret_folder,
                value,
                add_machines=[self.machine.name] if deployed else [],
                add_groups=self.machine.deployment["sops"]["defaultGroups"],
                git_commit=False,
            )
        return secret_folder

    def get(self, generator_name: str, name: str, shared: bool = False) -> bytes:
        return decrypt_secret(
            self.machine.flake_dir, self.secret_path(generator_name, name, shared)
        ).encode("utf-8")

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

    def exists_shared(self, generator_name: str, name: str) -> bool:
        secret_folder = self.secret_path(generator_name, name, shared=True)
        return (secret_folder / "secret").exists()

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        secret_folder = self.secret_path(generator_name, name, shared)
        if not (secret_folder / "secret").exists():
            return False
        if not shared:
            return True
        return self.machine_has_access(generator_name, name, shared)
