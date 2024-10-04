import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from clan_cli.dirs import user_config_dir
from clan_cli.errors import ClanError
from clan_cli.git import commit_files
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.secrets.folders import sops_machines_folder, sops_secrets_folder
from clan_cli.secrets.machines import add_secret
from clan_cli.secrets.secrets import (
    allow_member,
    collect_keys_for_path,
    decrypt_secret,
    groups_folder,
    has_secret,
    machines_folder,
    users_folder,
)
from clan_cli.secrets.sops import (
    decrypt_file,
    encrypt_file,
    generate_private_key,
    read_key,
)

from . import SecretStoreBase


@dataclass
class SopsKey:
    pubkey: str
    username: str


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

        # exit early if the machine already exists
        if (self.sops_dir / "machines" / self.machine.name / "key.json").exists():
            return

        priv_key, pub_key = generate_private_key()
        self.encrypt_secret(
            self.sops_dir / "secrets" / f"{self.machine.name}-age.key",
            priv_key,
        )
        self.add_machine(self.machine.name, pub_key)

    @property
    def sops_dir(self) -> Path:
        return self.machine.flake_dir / "sops"

    @property
    def store_name(self) -> str:
        return "sops"

    def add_machine(self, machine: str, pubkey: str) -> None:
        machine_path = self.sops_dir / "machines" / machine
        self.write_key(machine_path, pubkey)
        paths = [machine_path]
        commit_files(
            paths,
            self.machine.flake_dir,
            f"Add machine {machine} to secrets",
        )

    def write_key(self, machine_path: Path, publickey: str) -> None:
        machine_path.mkdir(parents=True, exist_ok=True)
        try:
            flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_EXCL
            fd = os.open(machine_path / "key.json", flags)
        except FileExistsError as e:
            msg = f"{machine_path.name} already exists in {machine_path}"
            raise ClanError(msg) from e
        with os.fdopen(fd, "w") as f:
            json.dump({"publickey": publickey, "type": "age"}, f, indent=2)

    def default_admin_key_path(self) -> Path:
        raw_path = os.environ.get("SOPS_AGE_KEY_FILE")
        if raw_path:
            return Path(raw_path)
        return user_config_dir() / "sops" / "age" / "keys.txt"

    def get_public_key(self, privkey: str) -> str:
        cmd = nix_shell(["nixpkgs#age"], ["age-keygen", "-y"])
        try:
            res = subprocess.run(
                cmd, input=privkey, stdout=subprocess.PIPE, text=True, check=True
            )
        except subprocess.CalledProcessError as e:
            msg = "Failed to get public key for age private key. Is the key malformed?"
            raise ClanError(msg) from e
        return res.stdout.strip()

    def maybe_get_admin_public_key(self) -> str | None:
        key = os.environ.get("SOPS_AGE_KEY")
        if key:
            return self.get_public_key(key)
        path = self.default_admin_key_path()
        if path.exists():
            return self.get_public_key(path.read_text())

        return None

    # TODO: get rid of `clan secrets generate` dependency
    def admin_key(self) -> SopsKey:
        pub_key = self.maybe_get_admin_public_key()
        if not pub_key:
            msg = "No sops key found. Please generate one with 'clan secrets key generate'."
            raise ClanError(msg)
        # return SopsKey(pub_key, username="")
        return self.ensure_user_or_machine(pub_key)

    # TODO: find alternative to `clan secrets users add`
    def ensure_user_or_machine(self, pub_key: str) -> SopsKey:
        key = self.maybe_get_user_or_machine(pub_key)
        if not key:
            msg = f"Your sops key is not yet added to the repository. Please add it with 'clan secrets users add youruser {pub_key}' (replace youruser with your user name)"
            raise ClanError(msg)
        return key

    def maybe_get_user_or_machine(self, pub_key: str) -> SopsKey | None:
        key = SopsKey(pub_key, username="")
        folders = [self.sops_dir / "users", self.sops_dir / "machines"]

        for folder in folders:
            if folder.exists():
                for user in folder.iterdir():
                    if not (user / "key.json").exists():
                        continue
                    if read_key(user) == pub_key:
                        key.username = user.name
                        return key

        return None

    def encrypt_secret(
        self,
        secret_path: Path,
        value: IO[str] | str | bytes | None,
        add_machines: list[str] | None = None,
        add_groups: list[str] | None = None,
        git_commit: bool = True,
    ) -> None:
        if add_groups is None:
            add_groups = []
        if add_machines is None:
            add_machines = []
        key = self.admin_key()
        recipient_keys = set()

        files_to_commit = []
        for machine in add_machines:
            files_to_commit.extend(
                allow_member(
                    machines_folder(secret_path),
                    self.sops_dir / "machines",
                    machine,
                    False,
                )
            )

        for group in add_groups:
            files_to_commit.extend(
                allow_member(
                    groups_folder(secret_path),
                    self.sops_dir / "groups",
                    group,
                    False,
                )
            )

        recipient_keys = collect_keys_for_path(secret_path)

        if key.pubkey not in recipient_keys:
            recipient_keys.add(key.pubkey)
            files_to_commit.extend(
                allow_member(
                    users_folder(secret_path),
                    self.sops_dir / "users",
                    key.username,
                    False,
                )
            )

        secret_path = secret_path / "secret"
        encrypt_file(secret_path, value, sorted(recipient_keys))
        files_to_commit.append(secret_path)
        if git_commit:
            commit_files(
                files_to_commit,
                self.machine.flake_dir,
                f"Update secret {secret_path.parent.name}",
            )

    def decrypt_secret(self, secret_path: Path) -> str:
        path = secret_path / "secret"
        if not path.exists():
            msg = f"Secret '{secret_path!s}' does not exist"
            raise ClanError(msg)
        return decrypt_file(path)

    def machine_has_access(
        self, generator_name: str, secret_name: str, shared: bool
    ) -> bool:
        secret_path = self.secret_path(generator_name, secret_name, shared)
        secret = json.loads((secret_path / "secret").read_text())
        recipients = [r["recipient"] for r in secret["sops"]["age"]]
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
            self.encrypt_secret(
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
