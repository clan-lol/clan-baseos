import os
import subprocess
from itertools import chain
from pathlib import Path
from typing import override

from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

from . import SecretStoreBase


class SecretStore(SecretStoreBase):
    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        self.entry_prefix = "clan-vars"

    @property
    def store_name(self) -> str:
        return "password_store"

    @property
    def _password_store_dir(self) -> str:
        return os.environ.get(
            "PASSWORD_STORE_DIR", f"{os.environ['HOME']}/.password-store"
        )

    def entry_dir(self, generator_name: str, name: str, shared: bool) -> Path:
        return Path(self.entry_prefix) / self.rel_dir(generator_name, name, shared)

    def _set(
        self,
        generator_name: str,
        name: str,
        value: bytes,
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
                    str(self.entry_dir(generator_name, name, shared)),
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
                    str(self.entry_dir(generator_name, name, shared)),
                ],
            ),
            check=True,
            stdout=subprocess.PIPE,
        ).stdout

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        return (
            Path(self._password_store_dir)
            / f"{self.entry_dir(generator_name, name, shared)}.gpg"
        ).exists()

    def generate_hash(self) -> bytes:
        hashes = []
        hashes.append(
            subprocess.run(
                nix_shell(
                    ["nixpkgs#git"],
                    [
                        "git",
                        "-C",
                        self._password_store_dir,
                        "log",
                        "-1",
                        "--format=%H",
                        self.entry_prefix,
                    ],
                ),
                stdout=subprocess.PIPE,
                check=False,
            ).stdout.strip()
        )
        shared_dir = Path(self._password_store_dir) / self.entry_prefix / "shared"
        machine_dir = (
            Path(self._password_store_dir)
            / self.entry_prefix
            / "per-machine"
            / self.machine.name
        )
        for symlink in chain(shared_dir.glob("**/*"), machine_dir.glob("**/*")):
            if symlink.is_symlink():
                hashes.append(
                    subprocess.run(
                        nix_shell(
                            ["nixpkgs#git"],
                            [
                                "git",
                                "-C",
                                self._password_store_dir,
                                "log",
                                "-1",
                                "--format=%H",
                                str(symlink),
                            ],
                        ),
                        stdout=subprocess.PIPE,
                        check=False,
                    ).stdout.strip()
                )

        # we sort the hashes to make sure that the order is always the same
        hashes.sort()
        return b"\n".join(hashes)

    @override
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

    def upload(self, output_dir: Path) -> None:
        for secret_var in self.get_all():
            if not secret_var.deployed:
                continue
            rel_dir = self.rel_dir(
                secret_var.generator, secret_var.name, secret_var.shared
            )
            with (output_dir / rel_dir).open("wb") as f:
                f.write(
                    self.get(secret_var.generator, secret_var.name, secret_var.shared)
                )
        (output_dir / ".pass_info").write_bytes(self.generate_hash())
