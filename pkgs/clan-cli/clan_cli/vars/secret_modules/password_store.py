import os
from itertools import chain
from pathlib import Path
from typing import override

from clan_cli.cmd import run
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
        run(
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
        return run(
            nix_shell(
                ["nixpkgs#pass"],
                [
                    "pass",
                    "show",
                    str(self.entry_dir(generator_name, name, shared)),
                ],
            ),
        ).stdout.encode()

    def exists(self, generator_name: str, name: str, shared: bool = False) -> bool:
        return (
            Path(self._password_store_dir)
            / f"{self.entry_dir(generator_name, name, shared)}.gpg"
        ).exists()

    def generate_hash(self) -> bytes:
        hashes = []
        hashes.append(
            run(
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
                check=False,
            )
            .stdout.strip()
            .encode()
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
                    run(
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
                        check=False,
                    )
                    .stdout.strip()
                    .encode()
                )

        # we sort the hashes to make sure that the order is always the same
        hashes.sort()
        return b"\n".join(hashes)

    @override
    def needs_upload(self) -> bool:
        local_hash = self.generate_hash()
        remote_hash = self.machine.target_host.run(
            # TODO get the path to the secrets from the machine
            ["cat", f"{self.machine.secret_vars_upload_directory}/.pass_info"],
            check=False,
        ).stdout.strip()

        if not remote_hash:
            print("remote hash is empty")
            return True

        return local_hash.decode() != remote_hash

    def upload(self, output_dir: Path) -> None:
        for secret_var in self.get_all():
            if not secret_var.deployed:
                continue
            output_file = output_dir / "vars" / secret_var.generator / secret_var.name
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with (output_file).open("wb") as f:
                f.write(
                    self.get(secret_var.generator, secret_var.name, secret_var.shared)
                )
        (output_dir / ".pass_info").write_bytes(self.generate_hash())
