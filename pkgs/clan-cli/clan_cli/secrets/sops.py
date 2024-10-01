from __future__ import annotations

import enum
import io
import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO

from clan_cli.api import API
from clan_cli.cmd import Log, run
from clan_cli.dirs import user_config_dir
from clan_cli.errors import ClanError
from clan_cli.nix import nix_shell

from .folders import sops_machines_folder, sops_users_folder


class KeyType(enum.Enum):
    AGE = enum.auto()
    PGP = enum.auto()

    @classmethod
    def validate(cls, value: str | None) -> KeyType | None:  # noqa: ANN102
        if value:
            return cls.__members__.get(value.upper())
        return None


@dataclass
class SopsKey:
    pubkey: str
    username: str
    key_type: KeyType


def get_public_age_key(privkey: str) -> str:
    cmd = nix_shell(["nixpkgs#age"], ["age-keygen", "-y"])
    try:
        res = subprocess.run(
            cmd, input=privkey, stdout=subprocess.PIPE, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        msg = "Failed to get public key for age private key. Is the key malformed?"
        raise ClanError(msg) from e
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
            msg = "Could not find public key in age-keygen output"
            raise ClanError(msg)
        if not private_key:
            msg = "Could not find private key in age-keygen output"
            raise ClanError(msg)
        if out_file:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(res)
    except subprocess.CalledProcessError as e:
        msg = "Failed to generate private sops key"
        raise ClanError(msg) from e
    else:
        return private_key, pubkey


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


def maybe_get_user_or_machine(
    flake_dir: Path, pub_key: str, key_type: KeyType
) -> SopsKey | None:
    key = SopsKey(pub_key, username="", key_type=key_type)
    folders = [sops_users_folder(flake_dir), sops_machines_folder(flake_dir)]

    for folder in folders:
        if folder.exists():
            for user in folder.iterdir():
                if not (user / "key.json").exists():
                    continue
                if read_key(user) == (pub_key, key_type):
                    key.username = user.name
                    return key

    return None


@API.register
def ensure_user_or_machine(flake_dir: Path, pub_key: str, key_type: KeyType) -> SopsKey:
    key = maybe_get_user_or_machine(flake_dir, pub_key, key_type)
    if not key:
        msg = f"Your sops key is not yet added to the repository. Please add it with 'clan secrets users add youruser {pub_key}' (replace youruser with your user name)"
        raise ClanError(msg)
    return key


def default_admin_key_path() -> Path:
    raw_path = os.environ.get("SOPS_AGE_KEY_FILE")
    if raw_path:
        return Path(raw_path)
    return user_config_dir() / "sops" / "age" / "keys.txt"


@API.register
def maybe_get_admin_public_key() -> tuple[str, KeyType | None]:
    age_key = os.environ.get("SOPS_AGE_KEY")
    pgp_key = os.environ.get("SOPS_PGP_FP")
    if age_key and pgp_key:
        msg = "Cannot decide which key to use when both `SOPS_AGE_KEY` and `SOPS_PGP_FP` are set. Please specify one or the other."
        raise ClanError(msg)
    if age_key:
        return get_public_age_key(age_key), KeyType.AGE
    if pgp_key:
        return pgp_key, KeyType.PGP

    path = default_admin_key_path()
    if path.exists():
        return get_public_age_key(path.read_text()), KeyType.AGE

    return "", None


def maybe_get_sops_key(flake_dir: Path) -> SopsKey | None:
    pub_key, key_type = maybe_get_admin_public_key()
    if key_type:
        return maybe_get_user_or_machine(flake_dir, pub_key, key_type)
    return None


def ensure_admin_key(flake_dir: Path) -> SopsKey:
    pub_key, key_type = maybe_get_admin_public_key()
    if not key_type:
        msg = "No sops key found. Please generate one with 'clan secrets key generate'."
        raise ClanError(msg)
    return ensure_user_or_machine(flake_dir, pub_key, key_type)


@contextmanager
def sops_manifest(keys: list[tuple[str, KeyType]]) -> Iterator[Path]:
    all_keys: dict[str, list[str]] = {
        key_type.lower(): [] for key_type in KeyType.__members__
    }
    for key, key_type in keys:
        all_keys[key_type.name.lower()].append(key)
    with NamedTemporaryFile(delete=False, mode="w") as manifest:
        json.dump({"creation_rules": [{"key_groups": [all_keys]}]}, manifest, indent=2)
        manifest.flush()
        yield Path(manifest.name)


def update_keys(secret_path: Path, keys: list[tuple[str, KeyType]]) -> list[Path]:
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
    pubkeys: list[tuple[str, KeyType]],
) -> None:
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
                msg = (
                    f"Failed to encrypt {secret_path}: sops exited with {p.returncode}"
                )
                raise ClanError(msg)
            return

        # hopefully /tmp is written to an in-memory file to avoid leaking secrets
        with NamedTemporaryFile(delete=False) as f:
            try:
                if isinstance(content, str):
                    Path(f.name).write_text(content)
                elif isinstance(content, bytes):
                    Path(f.name).write_bytes(content)
                elif isinstance(content, io.IOBase):
                    with Path(f.name).open("w") as fd:
                        shutil.copyfileobj(content, fd)
                else:
                    msg = f"Invalid content type: {type(content)}"
                    raise ClanError(msg)
                # we pass an empty manifest to pick up existing configuration of the user
                args = ["sops", "--config", str(manifest)]
                args.extend(["-i", "--encrypt", str(f.name)])
                cmd = nix_shell(["nixpkgs#sops"], args)
                run(cmd, log=Log.BOTH)
                # atomic copy of the encrypted file
                with NamedTemporaryFile(dir=folder, delete=False) as f2:
                    shutil.copyfile(f.name, f2.name)
                    Path(f2.name).rename(secret_path)
            finally:
                with suppress(OSError):
                    Path(f.name).unlink()


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
    with meta_path.open() as f:
        return json.load(f)


def write_key(path: Path, publickey: str, key_type: KeyType, overwrite: bool) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        if not overwrite:
            flags |= os.O_EXCL
        fd = os.open(path / "key.json", flags)
    except FileExistsError as e:
        msg = f"{path.name} already exists in {path}. Use --force to overwrite."
        raise ClanError(msg) from e
    with os.fdopen(fd, "w") as f:
        contents = {"publickey": publickey, "type": key_type.name.lower()}
        json.dump(contents, f, indent=2)


def read_key(path: Path) -> tuple[str, KeyType]:
    with Path(path / "key.json").open() as f:
        try:
            key = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"Failed to decode {path.name}: {e}"
            raise ClanError(msg) from e
    key_type = KeyType.validate(key.get("type"))
    if key_type is None:
        msg = f"Invalid key type in {path.name}: \"{key_type}\" (expected one of {', '.join(KeyType.__members__.keys())})."
        raise ClanError(msg)
    publickey = key.get("publickey")
    if not publickey:
        msg = f"{path.name} does not contain a public key"
        raise ClanError(msg)
    return publickey, key_type
