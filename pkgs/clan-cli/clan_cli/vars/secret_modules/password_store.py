import io
import logging
import os
import tarfile
from itertools import chain
from pathlib import Path
from typing import override

from clan_cli.cmd import Log, run
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell

from . import SecretStoreBase

log = logging.getLogger(__name__)


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

        manifest = []
        for gen_name, generator in self.machine.vars_generators.items():
            for f_name in generator["files"]:
                manifest.append(f"{gen_name}/{f_name}".encode())
        manifest += hashes
        return b"\n".join(manifest)

    @override
    def needs_upload(self) -> bool:
        local_hash = self.generate_hash()
        remote_hash = self.machine.target_host.run(
            # TODO get the path to the secrets from the machine
            ["cat", f"{self.machine.secret_vars_upload_directory}/.pass_info"],
            log=Log.STDERR,
            check=False,
        ).stdout.strip()

        if not remote_hash:
            print("remote hash is empty")
            return True

        return local_hash.decode() != remote_hash

    def upload(self, output_dir: Path) -> None:
        with tarfile.open(output_dir / "secrets.tar.gz", "w:gz") as tar:
            for gen_name, generator in self.machine.vars_generators.items():
                tar_dir = tarfile.TarInfo(name=gen_name)
                tar_dir.type = tarfile.DIRTYPE
                tar_dir.mode = 0o511
                tar.addfile(tarinfo=tar_dir)
                for f_name, file in generator["files"].items():
                    if not file["deploy"]:
                        continue
                    if not file["secret"]:
                        continue
                    tar_file = tarfile.TarInfo(name=f"{gen_name}/{f_name}")
                    content = self.get(gen_name, f_name, generator["share"])
                    tar_file.size = len(content)
                    tar_file.mode = 0o440
                    tar_file.uname = file.get("owner", "root")
                    tar_file.gname = file.get("group", "root")
                    tar.addfile(tarinfo=tar_file, fileobj=io.BytesIO(content))
        (output_dir / ".pass_info").write_bytes(self.generate_hash())
