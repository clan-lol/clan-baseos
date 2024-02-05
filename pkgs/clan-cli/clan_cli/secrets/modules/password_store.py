import os
import subprocess
from pathlib import Path

from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell


class SecretStore:
    def __init__(self, machine: Machine) -> None:
        self.machine = machine

    def set(self, _service: str, name: str, value: bytes) -> Path | None:
        subprocess.run(
            nix_shell(
                ["nixpkgs#pass"],
                ["pass", "insert", "-m", f"machines/{self.machine.name}/{name}"],
            ),
            input=value,
            check=True,
        )
        return None  # we manage the files outside of the git repo

    def get(self, _service: str, name: str) -> bytes:
        return subprocess.run(
            nix_shell(
                ["nixpkgs#pass"],
                ["pass", "show", f"machines/{self.machine.name}/{name}"],
            ),
            check=True,
            stdout=subprocess.PIPE,
        ).stdout

    def exists(self, _service: str, name: str) -> bool:
        password_store = os.environ.get(
            "PASSWORD_STORE_DIR", f"{os.environ['HOME']}/.password-store"
        )
        secret_path = Path(password_store) / f"machines/{self.machine.name}/{name}.gpg"
        return secret_path.exists()

    def generate_hash(self) -> bytes:
        password_store = os.environ.get(
            "PASSWORD_STORE_DIR", f"{os.environ['HOME']}/.password-store"
        )
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

    def update_check(self) -> bool:
        local_hash = self.generate_hash()
        remote_hash = self.machine.host.run(
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
        for service in self.machine.secrets_data:
            for secret in self.machine.secrets_data[service]["secrets"]:
                (output_dir / secret).write_bytes(self.get(service, secret))
        (output_dir / ".pass_info").write_bytes(self.generate_hash())
