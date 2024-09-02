import contextlib
import shutil
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

from clan_cli.errors import ClanError
from clan_cli.nix import nix_shell


@contextlib.contextmanager
def start_virtiofsd(socket_path: Path) -> Iterator[None]:
    sandbox = "namespace"
    if shutil.which("newuidmap") is None:
        sandbox = "none"
    virtiofsd = nix_shell(
        ["nixpkgs#virtiofsd"],
        [
            "virtiofsd",
            "--socket-path",
            str(socket_path),
            "--cache",
            "always",
            "--sandbox",
            sandbox,
            "--shared-dir",
            "/nix/store",
        ],
    )
    with subprocess.Popen(virtiofsd) as proc:
        try:
            while not socket_path.exists():
                rc = proc.poll()
                if rc is not None:
                    msg = f"virtiofsd exited unexpectedly with code {rc}"
                    raise ClanError(msg)
                time.sleep(0.1)
            yield
        finally:
            proc.kill()
