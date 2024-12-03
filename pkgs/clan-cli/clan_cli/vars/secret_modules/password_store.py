import io
import logging
import os
import tarfile
from itertools import chain
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import Log, RunOpts, run
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.ssh.upload import upload
from clan_cli.vars.generate import Generator, Var

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

    def entry_dir(self, generator: Generator, name: str) -> Path:
        return Path(self.entry_prefix) / self.rel_dir(generator, name)

    def _set(
        self,
        generator: Generator,
        var: Var,
        value: bytes,
    ) -> Path | None:
        run(
            nix_shell(
                ["nixpkgs#pass"],
                [
                    "pass",
                    "insert",
                    "-m",
                    str(self.entry_dir(generator, var.name)),
                ],
            ),
            RunOpts(input=value, check=True),
        )
        return None  # we manage the files outside of the git repo

    def get(self, generator: Generator, name: str) -> bytes:
        return run(
            nix_shell(
                ["nixpkgs#pass"],
                [
                    "pass",
                    "show",
                    str(self.entry_dir(generator, name)),
                ],
            ),
        ).stdout.encode()

    def exists(self, generator: Generator, name: str) -> bool:
        return (
            Path(self._password_store_dir) / f"{self.entry_dir(generator, name)}.gpg"
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
                RunOpts(check=False),
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
                        RunOpts(check=False),
                    )
                    .stdout.strip()
                    .encode()
                )

        # we sort the hashes to make sure that the order is always the same
        hashes.sort()

        manifest = []
        for generator in self.machine.vars_generators:
            for file in generator.files:
                manifest.append(f"{generator.name}/{file.name}".encode())
        manifest += hashes
        return b"\n".join(manifest)

    def needs_upload(self) -> bool:
        local_hash = self.generate_hash()
        remote_hash = self.machine.target_host.run(
            # TODO get the path to the secrets from the machine
            [
                "cat",
                f"{self.machine.deployment["password-store"]["secretLocation"]}/.pass_info",
            ],
            RunOpts(log=Log.STDERR, check=False),
        ).stdout.strip()

        if not remote_hash:
            print("remote hash is empty")
            return True

        return local_hash.decode() != remote_hash

    def populate_dir(self, output_dir: Path) -> None:
        with tarfile.open(output_dir / "secrets.tar.gz", "w:gz") as tar:
            for generator in self.machine.vars_generators:
                dir_exists = False
                for file in generator.files:
                    if not file.deploy:
                        continue
                    if not file.secret:
                        continue
                    if not dir_exists:
                        tar_dir = tarfile.TarInfo(name=generator.name)
                        tar_dir.type = tarfile.DIRTYPE
                        tar_dir.mode = 0o511
                        tar.addfile(tarinfo=tar_dir)
                        dir_exists = True
                    tar_file = tarfile.TarInfo(name=f"{generator.name}/{file.name}")
                    content = self.get(generator, file.name)
                    tar_file.size = len(content)
                    tar_file.mode = 0o440
                    tar_file.uname = file.owner
                    tar_file.gname = file.group
                    tar.addfile(tarinfo=tar_file, fileobj=io.BytesIO(content))
        (output_dir / ".pass_info").write_bytes(self.generate_hash())

    def upload(self) -> None:
        if not self.needs_upload():
            log.info("Secrets already uploaded")
            return
        with TemporaryDirectory(prefix="vars-upload-") as tempdir:
            pass_dir = Path(tempdir)
            upload_dir = Path(
                self.machine.deployment["password-store"]["secretLocation"]
            )
            upload(self.machine.target_host, pass_dir, upload_dir)
