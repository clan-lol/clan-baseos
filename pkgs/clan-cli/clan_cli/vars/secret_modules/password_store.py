import os
import subprocess
from pathlib import Path

from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

from . import SecretStoreBase


class SecretStore(SecretStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine

    @property
    def _password_store_dir(self) -> str:
        return os.environ.get(
            "PASSWORD_STORE_DIR", f"{os.environ['HOME']}/.password-store"
        )

    def _var_path(self, generator_name: str, name: str, shared: bool) -> Path:
        if shared:
            return Path(f"shared/{generator_name}/{name}")
        return Path(f"machines/{self.machine.name}/{generator_name}/{name}")

    def set(
        self,
        generator_name: str,
        name: str,
        value: bytes,
        groups: list[str],
        shared: bool = False,
        deployed: bool = True,
    ) -> Path | None:
        subprocess.run(
            nix_shell(
                ["nixpkgs#pass"],
                [
                    "pass",
                    "insert",
                    "-m",
                    str(self._var_path(generator_name, name, shared)),
                ],
            ),
            input=value,
            check=True,
        )
        return None  # we manage the files outside of the git repo

    def get(self, generator_name: str, name: str, shared: bool = False) -> bytes:
        return subprocess.run(
            nix_shell(
                ["nixpkgs#pass"],
                [
                    "pass",
                    "show",
                    str(self._var_path(generator_name, name, shared)),
                ],
            ),
            check=True,
            stdout=subprocess.PIPE,
        ).stdout

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        return (
            Path(self._password_store_dir)
            / f"{self._var_path(generator_name, name, shared)}.gpg"
        ).exists()

    def generate_hash(self) -> bytes:
        password_store = self._password_store_dir
        hashes = []
        hashes.append(
            subprocess.run(
                nix_shell(
                    ["nixpkgs#git"],
                    [
                        "git",
                        "-C",
                        password_store,
                        "log",
                        "-1",
                        "--format=%H",
                        f"machines/{self.machine.name}",
                    ],
                ),
                stdout=subprocess.PIPE,
            ).stdout.strip()
        )
        for symlink in Path(password_store).glob(f"machines/{self.machine.name}/**/*"):
            if symlink.is_symlink():
                hashes.append(
                    subprocess.run(
                        nix_shell(
                            ["nixpkgs#git"],
                            [
                                "git",
                                "-C",
                                password_store,
                                "log",
                                "-1",
                                "--format=%H",
                                str(symlink),
                            ],
                        ),
                        stdout=subprocess.PIPE,
                    ).stdout.strip()
                )

        # we sort the hashes to make sure that the order is always the same
        hashes.sort()
        return b"\n".join(hashes)

    # FIXME: add this when we switch to python3.12
    # @override
    def update_check(self) -> bool:
        local_hash = self.generate_hash()
        remote_hash = self.machine.target_host.run(
            # TODO get the path to the secrets from the machine
            ["cat", f"{self.machine.secrets_upload_directory}/.pass_info"],
            check=False,
            stdout=subprocess.PIPE,
        ).stdout.strip()

        if not remote_hash:
            print("remote hash is empty")
            return False

        return local_hash.decode() == remote_hash

    # TODO: fixme
    def upload(self, output_dir: Path) -> None:
        pass
        # for service in self.machine.facts_data:
        #     for secret in self.machine.facts_data[service]["secret"]:
        #         if isinstance(secret, dict):
        #             secret_name = secret["name"]
        #         else:
        #             # TODO: drop old format soon
        #             secret_name = secret
        #         with (output_dir / secret_name).open("wb") as f:
        #            f.chmod(0o600)
        #            f.write(self.get(service, secret_name))
        # (output_dir / ".pass_info").write_bytes(self.generate_hash())
