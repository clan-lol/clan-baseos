import io
import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO

from clan_cli.cmd import Log, run
from clan_cli.dirs import user_config_dir
from clan_cli.errors import ClanError
from clan_cli.nix import nix_shell

from .folders import sops_machines_folder, sops_users_folder


class SopsKey:
    def __init__(self, pubkey: str, username: str) -> None:
        self.pubkey = pubkey
        self.username = username


def get_public_key(privkey: str) -> str:
    cmd = nix_shell(["nixpkgs#age"], ["age-keygen", "-y"])
    try:
        res = subprocess.run(
            cmd, input=privkey, stdout=subprocess.PIPE, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        raise ClanError(
            "Failed to get public key for age private key. Is the key malformed?"
        ) from e
    return res.stdout.strip()


def generate_private_key(out_file: Path | None = None) -> tuple[str, str]:
    cmd = nix_shell(["nixpkgs#age"], ["age-keygen"])
    try:
        proc = run(cmd)
        res = proc.stdout.strip()
        pubkey = None
        private_key = None
        for line in res.splitlines():
            if line.startswith("# public key:"):
                pubkey = line.split(":")[1].strip()
            if not line.startswith("#"):
                private_key = line
        if not pubkey:
            raise ClanError("Could not find public key in age-keygen output")
        if not private_key:
            raise ClanError("Could not find private key in age-keygen output")
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(res)
        return private_key, pubkey
    except subprocess.CalledProcessError as e:
        raise ClanError("Failed to generate private sops key") from e


def get_user_name(flake_dir: Path, user: str) -> str:
    """Ask the user for their name until a unique one is provided."""
    while True:
        name = input(
            f"Your key is not yet added to the repository. Enter your user name for which your sops key will be stored in the repository [default: {user}]: "
        )
        if name:
            user = name
        if not (flake_dir / user).exists():
            return user
        print(f"{flake_dir / user} already exists")


def ensure_user_or_machine(flake_dir: Path, pub_key: str) -> SopsKey:
    key = SopsKey(pub_key, username="")
    folders = [sops_users_folder(flake_dir), sops_machines_folder(flake_dir)]

    for folder in folders:
        if folder.exists():
            for user in folder.iterdir():
                if not (user / "key.json").exists():
                    continue
                if read_key(user) == pub_key:
                    key.username = user.name
                    return key

    raise ClanError(
        f"Your sops key is not yet added to the repository. Please add it with 'clan secrets users add youruser {pub_key}' (replace youruser with your user name)"
    )


def default_sops_key_path() -> Path:
    raw_path = os.environ.get("SOPS_AGE_KEY_FILE")
    if raw_path:
        return Path(raw_path)
    else:
        return user_config_dir() / "sops" / "age" / "keys.txt"


def ensure_sops_key(flake_dir: Path) -> SopsKey:
    key = os.environ.get("SOPS_AGE_KEY")
    if key:
        return ensure_user_or_machine(flake_dir, get_public_key(key))
    path = default_sops_key_path()
    if path.exists():
        return ensure_user_or_machine(flake_dir, get_public_key(path.read_text()))
    else:
        raise ClanError(
            "No sops key found. Please generate one with 'clan secrets key generate'."
        )


@contextmanager
def sops_manifest(keys: list[str]) -> Iterator[Path]:
    with NamedTemporaryFile(delete=False, mode="w") as manifest:
        json.dump(
            dict(creation_rules=[dict(key_groups=[dict(age=keys)])]), manifest, indent=2
        )
        manifest.flush()
        yield Path(manifest.name)


def update_keys(secret_path: Path, keys: list[str]) -> list[Path]:
    with sops_manifest(keys) as manifest:
        secret_path = secret_path / "secret"
        time_before = secret_path.stat().st_mtime
        cmd = nix_shell(
            ["nixpkgs#sops"],
            [
                "sops",
                "--config",
                str(manifest),
                "updatekeys",
                "--yes",
                str(secret_path),
            ],
        )
        run(cmd, log=Log.BOTH, error_msg=f"Could not update keys for {secret_path}")
        if time_before == secret_path.stat().st_mtime:
            return []
        return [secret_path]


def encrypt_file(
    secret_path: Path,
    content: IO[str] | str | bytes | None,
    pubkeys: list[str],
    meta: dict | None = None,
) -> None:
    if meta is None:
        meta = {}
    folder = secret_path.parent
    folder.mkdir(parents=True, exist_ok=True)

    with sops_manifest(pubkeys) as manifest:
        if not content:
            args = ["sops", "--config", str(manifest)]
            args.extend([str(secret_path)])
            cmd = nix_shell(["nixpkgs#sops"], args)
            # Don't use our `run` here, because it breaks editor integration.
            # We never need this in our UI.
            p = subprocess.run(cmd, check=False)
            # returns 200 if the file is changed
            if p.returncode != 0 and p.returncode != 200:
                raise ClanError(
                    f"Failed to encrypt {secret_path}: sops exited with {p.returncode}"
                )
            return

        # hopefully /tmp is written to an in-memory file to avoid leaking secrets
        with NamedTemporaryFile(delete=False) as f:
            try:
                if isinstance(content, str):
                    with open(f.name, "w") as fd:
                        fd.write(content)
                elif isinstance(content, bytes):
                    with open(f.name, "wb") as fd:
                        fd.write(content)
                elif isinstance(content, io.IOBase):
                    with open(f.name, "w") as fd:
                        shutil.copyfileobj(content, fd)
                else:
                    raise ClanError(f"Invalid content type: {type(content)}")
                # we pass an empty manifest to pick up existing configuration of the user
                args = ["sops", "--config", str(manifest)]
                args.extend(["-i", "--encrypt", str(f.name)])
                cmd = nix_shell(["nixpkgs#sops"], args)
                run(cmd, log=Log.BOTH)
                # atomic copy of the encrypted file
                with NamedTemporaryFile(dir=folder, delete=False) as f2:
                    shutil.copyfile(f.name, f2.name)
                    os.rename(f2.name, secret_path)
                meta_path = secret_path.parent / "meta.json"
                with open(meta_path, "w") as f_meta:
                    json.dump(meta, f_meta, indent=2)
            finally:
                try:
                    os.remove(f.name)
                except OSError:
                    pass


def decrypt_file(secret_path: Path) -> str:
    with sops_manifest([]) as manifest:
        cmd = nix_shell(
            ["nixpkgs#sops"],
            ["sops", "--config", str(manifest), "--decrypt", str(secret_path)],
        )
    res = run(cmd, error_msg=f"Could not decrypt {secret_path}")
    return res.stdout


def get_meta(secret_path: Path) -> dict:
    meta_path = secret_path.parent / "meta.json"
    if not meta_path.exists():
        return {}
    with open(meta_path) as f:
        return json.load(f)


def write_key(path: Path, publickey: str, overwrite: bool) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        if not overwrite:
            flags |= os.O_EXCL
        fd = os.open(path / "key.json", flags)
    except FileExistsError as e:
        raise ClanError(
            f"{path.name} already exists in {path}. Use --force to overwrite."
        ) from e
    with os.fdopen(fd, "w") as f:
        json.dump({"publickey": publickey, "type": "age"}, f, indent=2)


def read_key(path: Path) -> str:
    with open(path / "key.json") as f:
        try:
            key = json.load(f)
        except json.JSONDecodeError as e:
            raise ClanError(f"Failed to decode {path.name}: {e}") from e
    if key["type"] != "age":
        raise ClanError(
            f"{path.name} is not an age key but {key['type']}. This is not supported"
        )
    publickey = key.get("publickey")
    if not publickey:
        raise ClanError(f"{path.name} does not contain a public key")
    return publickey
