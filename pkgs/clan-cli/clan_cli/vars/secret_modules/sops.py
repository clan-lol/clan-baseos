from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import override

from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine
from clan_cli.secrets import sops
from clan_cli.secrets.folders import (
    sops_groups_folder,
    sops_machines_folder,
    sops_secrets_folder,
    sops_users_folder,
)
from clan_cli.secrets.machines import add_machine, add_secret, has_machine
from clan_cli.secrets.secrets import (
    allow_member,
    collect_keys_for_path,
    decrypt_secret,
    encrypt_secret,
    groups_folder,
    has_secret,
)
from clan_cli.ssh.upload import upload
from clan_cli.vars._types import StoreBase
from clan_cli.vars.generate import Generator
from clan_cli.vars.var import Var


@dataclass
class SopsKey:
    pubkey: str
    username: str


class MissingKeyError(ClanError):
    def __init__(self) -> None:
        msg = "Cannot find admin keys for current $USER on this computer. Please initialize admin keys once with 'clan vars keygen'"
        super().__init__(msg)


class SecretStore(StoreBase):
    @property
    def is_secret_store(self) -> bool:
        return True

    def __init__(self, machine: Machine) -> None:
        self.machine = machine

        # no need to generate keys if we don't manage secrets
        if not self.machine.vars_generators:
            return
        has_secrets = False
        for generator in self.machine.vars_generators:
            for file in generator.files:
                if file.secret:
                    has_secrets = True
        if not has_secrets:
            return

        if has_machine(self.machine.flake_dir, self.machine.name):
            return
        priv_key, pub_key = sops.generate_private_key()
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

    def user_has_access(
        self, user: str, generator: Generator, secret_name: str
    ) -> bool:
        key_dir = sops_users_folder(self.machine.flake_dir) / user
        return self.key_has_access(key_dir, generator, secret_name)

    def machine_has_access(self, generator: Generator, secret_name: str) -> bool:
        key_dir = sops_machines_folder(self.machine.flake_dir) / self.machine.name
        return self.key_has_access(key_dir, generator, secret_name)

    def key_has_access(
        self, key_dir: Path, generator: Generator, secret_name: str
    ) -> bool:
        secret_path = self.secret_path(generator, secret_name)
        recipient = sops.SopsKey.load_dir(key_dir)
        recipients = sops.get_recipients(secret_path)
        return recipient in recipients

    def secret_path(self, generator: Generator, secret_name: str) -> Path:
        return self.directory(generator, secret_name)

    @override
    def health_check(
        self, generator: Generator | None = None, file_name: str | None = None
    ) -> str | None:
        """
        Apply local updates to secrets like re-encrypting with missing keys
            when new users were added.
        """

        if generator is None:
            generators = self.machine.vars_generators
        else:
            generators = [generator]
        file_found = False
        outdated = []
        for generator in generators:
            for file in generator.files:
                # if we check only a single file, continue on all the other ones
                if file_name:
                    if file.name == file_name:
                        file_found = True
                    else:
                        continue
                if file.secret and self.exists(generator, file.name):
                    if file.deploy:
                        self.ensure_machine_has_access(generator, file.name)
                    needs_update, msg = self.needs_fix(generator, file.name)
                    if needs_update:
                        outdated.append((generator.name, file.name, msg))
        if file_name and not file_found:
            msg = f"file {file_name} was not found"
            raise ClanError(msg)
        if outdated:
            msg = (
                "The local state of some secret vars is inconsistent and needs to be updated.\n"
                f"Run 'clan vars fix {self.machine.name}' to apply the necessary changes."
                "Problems to fix:\n"
                "\n".join(o[2] for o in outdated if o[2])
            )
            return msg
        return None

    def _set(
        self,
        generator: Generator,
        var: Var,
        value: bytes,
    ) -> Path | None:
        secret_folder = self.secret_path(generator, var.name)
        # create directory if it doesn't exist
        secret_folder.mkdir(parents=True, exist_ok=True)
        # initialize the secret
        encrypt_secret(
            self.machine.flake_dir,
            secret_folder,
            value,
            add_machines=[self.machine.name] if var.deploy else [],
            add_groups=self.machine.deployment["sops"]["defaultGroups"],
            git_commit=False,
        )
        return secret_folder

    def get(self, generator: Generator, name: str) -> bytes:
        return decrypt_secret(
            self.machine.flake_dir, self.secret_path(generator, name)
        ).encode("utf-8")

    def populate_dir(self, output_dir: Path, phases: list[str]) -> None:
        if "users" in phases or "services" in phases:
            key_name = f"{self.machine.name}-age.key"
            if not has_secret(sops_secrets_folder(self.machine.flake_dir) / key_name):
                # skip uploading the secret, not managed by us
                return
            key = decrypt_secret(
                self.machine.flake_dir,
                sops_secrets_folder(self.machine.flake_dir) / key_name,
            )
            (output_dir / "key.txt").touch(mode=0o600)
            (output_dir / "key.txt").write_text(key)

        if "activation" in phases:
            for generator in self.machine.vars_generators:
                for file in generator.files:
                    if file.needed_for == "activation":
                        target_path = (
                            output_dir / "activation" / generator.name / file.name
                        )
                        target_path.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        # chmod after in case it doesn't have u+w
                        target_path.touch(mode=0o600)
                        target_path.write_bytes(self.get(generator, file.name))
                        target_path.chmod(file.mode)

        if "partitioning" in phases:
            for generator in self.machine.vars_generators:
                for file in generator.files:
                    if file.needed_for == "partitioning":
                        target_path = output_dir / generator.name / file.name
                        target_path.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                        # chmod after in case it doesn't have u+w
                        target_path.touch(mode=0o600)
                        target_path.write_bytes(self.get(generator, file.name))
                        target_path.chmod(file.mode)

    def upload(self, phases: list[str]) -> None:
        if "partitioning" in phases:
            msg = "Cannot upload partitioning secrets"
            raise NotImplementedError(msg)
        with TemporaryDirectory(prefix="sops-upload-") as tempdir:
            sops_upload_dir = Path(tempdir)
            self.populate_dir(sops_upload_dir, phases)
            upload(self.machine.target_host, sops_upload_dir, Path("/var/lib/sops-nix"))

    def exists(self, generator: Generator, name: str) -> bool:
        secret_folder = self.secret_path(generator, name)
        return (secret_folder / "secret").exists()

    def ensure_machine_has_access(self, generator: Generator, name: str) -> None:
        if self.machine_has_access(generator, name):
            return
        secret_folder = self.secret_path(generator, name)
        add_secret(self.machine.flake_dir, self.machine.name, secret_folder)

    def collect_keys_for_secret(self, path: Path) -> set[sops.SopsKey]:
        from clan_cli.secrets.secrets import (
            collect_keys_for_path,
            collect_keys_for_type,
        )

        keys = collect_keys_for_path(path)
        for group in self.machine.deployment["sops"]["defaultGroups"]:
            keys.update(
                collect_keys_for_type(
                    self.machine.flake_dir / "sops" / "groups" / group / "machines"
                )
            )
            keys.update(
                collect_keys_for_type(
                    self.machine.flake_dir / "sops" / "groups" / group / "users"
                )
            )

        return {
            sops.SopsKey(pubkey=key, username="", key_type=key_type)
            for (key, key_type) in keys
        }

    #        }
    def needs_fix(self, generator: Generator, name: str) -> tuple[bool, str | None]:
        secret_path = self.secret_path(generator, name)
        current_recipients = sops.get_recipients(secret_path)
        wanted_recipients = self.collect_keys_for_secret(secret_path)
        needs_update = current_recipients != wanted_recipients
        recipients_to_add = wanted_recipients - current_recipients
        var_id = f"{generator.name}/{name}"
        msg = (
            f"One or more recipient keys were added to secret{' shared' if generator.share else ''} var '{var_id}', but it was never re-encrypted.\n"
            f"This could have been a malicious actor trying to add their keys, please investigate.\n"
            f"Added keys: {', '.join(f'{r.key_type.name}:{r.pubkey}' for r in recipients_to_add)}\n"
            f"If this is intended, run 'clan vars fix' to re-encrypt the secret."
        )
        return needs_update, msg

    @override
    def fix(
        self, generator: Generator | None = None, file_name: str | None = None
    ) -> None:
        from clan_cli.secrets.secrets import update_keys

        if generator is None:
            generators = self.machine.vars_generators
        else:
            generators = [generator]
        file_found = False
        for generator in generators:
            for file in generator.files:
                # if we check only a single file, continue on all the other ones
                if file_name:
                    if file.name == file_name:
                        file_found = True
                    else:
                        continue
                if not file.secret:
                    continue

                secret_path = self.secret_path(generator, file.name)

                for group in self.machine.deployment["sops"]["defaultGroups"]:
                    allow_member(
                        groups_folder(secret_path),
                        sops_groups_folder(self.machine.flake_dir),
                        group,
                        # we just want to create missing symlinks, we call update_keys below:
                        do_update_keys=False,
                    )

                update_keys(
                    secret_path,
                    collect_keys_for_path(secret_path),
                )
        if file_name and not file_found:
            msg = f"file {file_name} was not found"
            raise ClanError(msg)
