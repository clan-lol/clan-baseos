import enum
import functools
import io
import json
import logging
import os
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, Any, Protocol

from clan_cli.api import API
from clan_cli.cmd import Log, run
from clan_cli.dirs import user_config_dir
from clan_cli.errors import ClanError, CmdOut
from clan_cli.nix import nix_shell

from .folders import sops_machines_folder, sops_users_folder

log = logging.getLogger(__name__)


class KeyType(enum.Enum):
    AGE = enum.auto()
    PGP = enum.auto()

    @classmethod
    def validate(cls, value: str | None) -> "KeyType | None":  # noqa: ANN102
        if value:
            return cls.__members__.get(value.upper())
        return None


@dataclass(frozen=True, eq=False)
class SopsKey:
    pubkey: str
    username: str
    key_type: KeyType

    def as_dict(self) -> dict[str, str]:
        return {
            "publickey": self.pubkey,
            "username": self.username,
            "type": self.key_type.name.lower(),
        }


class ExitStatus(enum.IntEnum): # see: cmd/sops/codes/codes.go
    ERROR_GENERIC = 1
    COULD_NOT_READ_INPUT_FILE = 2
    COULD_NOT_WRITE_OUTPUT_FILE = 3
    ERROR_DUMPING_TREE = 4
    ERROR_READING_CONFIG = 5
    ERROR_INVALID_KMS_ENCRYPTION_CONTEXT_FORMAT = 6
    ERROR_INVALID_SET_FORMAT = 7
    ERROR_CONFLICTING_PARAMETERS = 8
    ERROR_ENCRYPTING_MAC = 21
    ERROR_ENCRYPTING_TREE = 23
    ERROR_DECRYPTING_MAC = 24
    ERROR_DECRYPTING_TREE = 25
    CANNOT_CHANGE_KEYS_FROM_NON_EXISTENT_FILE = 49
    MAC_MISMATCH = 51
    MAC_NOT_FOUND = 52
    CONFIG_FILE_NOT_FOUND = 61
    KEYBOARD_INTERRUPT = 85
    INVALID_TREE_PATH_FORMAT = 91
    NEED_AT_LEAST_ONE_DOCUMENT = 92
    NO_FILE_SPECIFIED = 100
    COULD_NOT_RETRIEVE_KEY = 128
    NO_ENCRYPTION_KEY_FOUND = 111
    DUPLICATE_DECRYPTION_KEY_TYPE = 112
    FILE_HAS_NOT_BEEN_MODIFIED = 200
    NO_EDITOR_FOUND = 201
    FAILED_TO_COMPARE_VERSIONS = 202
    FILE_ALREADY_ENCRYPTED = 203

    @classmethod
    def parse(cls, code: int) -> "ExitStatus | None":  # noqa: ANN102
        return ExitStatus(code) if code in ExitStatus else None


class Executor(Protocol):
    def __call__(
        self, cmd: list[str], *, env: dict[str, str] | None = None
    ) -> CmdOut: ...


class Operation(enum.StrEnum):
    decrypt = "decrypt"
    edit = "edit"
    encrypt = "encrypt"
    update_keys = "updatekeys"

    def __call__(
        self,
        secret_path: Path,
        public_keys: Iterable[tuple[str, KeyType]],
        executor: Executor,
    ) -> tuple[int, str]:
        sops_cmd = ["sops"]
        environ = os.environ.copy()
        with NamedTemporaryFile(delete=False, mode="w") as manifest:
            if self == Operation.decrypt:
                sops_cmd.append("decrypt")
            else:
                # When sops is used to edit a file the config is only used at
                # file creation, otherwise the keys from the exising file are
                # used.
                sops_cmd.extend(["--config", manifest.name])

                keys_by_type: dict[KeyType, list[str]] = {}
                keys_by_type = {key_type: [] for key_type in KeyType}
                for key, key_type in public_keys:
                    keys_by_type[key_type].append(key)
                it = keys_by_type.items()
                key_groups = [{key_type.name.lower(): keys for key_type, keys in it}]
                rules = {"creation_rules": [{"key_groups": key_groups}]}
                json.dump(rules, manifest, indent=2)
                manifest.flush()

                if self == Operation.encrypt:
                    # Remove SOPS env vars used to specify public keys to force
                    # sops to use our config file [1]; so that the file gets
                    # encrypted with our keys and not something leaking out of
                    # the environment.
                    #
                    # [1]: https://github.com/getsops/sops/blob/8c567aa8a7cf4802e251e87efc84a1c50b69d4f0/cmd/sops/main.go#L2229
                    for var in os.environ:
                        if var.startswith("SOPS_") and var not in { # allowed:
                            "SOPS_GPG_EXEC",
                            "SOPS_AGE_KEY",
                            "SOPS_AGE_KEY_FILE",
                            "SOPS_NIX_SECRET",
                        }:
                            del environ[var]
                    sops_cmd.extend(["encrypt", "--in-place"])
                elif self == Operation.update_keys:
                    sops_cmd.extend(["updatekeys", "--yes"])
                elif self != Operation.edit:
                    known_operations = ",".join(Operation.__members__.values())
                    msg = (
                        f"Unsupported sops operation {self.value} "
                        f"(known operations: {known_operations})"
                    )
                    raise ClanError(msg)
            sops_cmd.append(str(secret_path))

            cmd = nix_shell(["nixpkgs#sops"], sops_cmd)
            p = executor(cmd, env=environ)
            return p.returncode, p.stdout


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


def maybe_get_user_or_machine(flake_dir: Path, key: SopsKey) -> SopsKey | None:
    folders = [sops_users_folder(flake_dir), sops_machines_folder(flake_dir)]

    for folder in folders:
        if folder.exists():
            for user in folder.iterdir():
                if not (user / "key.json").exists():
                    continue
                this_pub_key, this_key_type = read_key(user)
                if key.pubkey == this_pub_key and key.key_type == this_key_type:
                    return SopsKey(key.pubkey, user.name, key.key_type)

    return None


@API.register
def ensure_user_or_machine(flake_dir: Path, key: SopsKey) -> SopsKey:
    maybe_key = maybe_get_user_or_machine(flake_dir, key)
    if maybe_key:
        return maybe_key
    msg = f"Your sops key is not yet added to the repository. Please add it with 'clan secrets users add youruser {key.pubkey}' (replace youruser with your user name)"
    raise ClanError(msg)


def default_admin_private_key_path() -> Path:
    raw_path = os.environ.get("SOPS_AGE_KEY_FILE")
    if raw_path:
        return Path(raw_path)
    return user_config_dir() / "sops" / "age" / "keys.txt"


@API.register
def maybe_get_admin_public_key() -> None | SopsKey:
    keyring = collect_public_keys()
    if len(keyring) == 0:
        return None

    if len(keyring) > 1:
        # louis@(2024-10-22):
        #
        # This is confusing when it shows up and you have no information
        # about where each key is going from, could we log the discovery
        # of each key?
        msg = (
            f"Found more than {len(keyring)} public keys in your "
            f"environment/system and cannot decide which one to "
            f"use, first three:\n\n"
            f"- {'\n- '.join(str(key.as_dict()) for key in keyring[:3])}\n\n"
            f"Please set one of SOPS_AGE_KEY, SOPS_AGE_KEY_FILE or "
            f"SOPS_PGP_FP appropriately"
        )
        raise ClanError(msg)

    return keyring[0]


def collect_public_keys() -> Sequence[SopsKey]:
    username = ""
    keyring: list[SopsKey] = []

    for private_key in collect_private_age_keys():
        public_key = get_public_age_key(private_key)
        keyring.append(SopsKey(public_key, username, KeyType.AGE))

    if pgp_fingerprints := os.environ.get("SOPS_PGP_FP"):
        for fp in pgp_fingerprints.strip().split(","):
            keyring.append(SopsKey(fp, username, KeyType.PGP))

    return keyring


def collect_private_age_keys() -> Sequence[str]:
    private_age_keys: list[str] = []

    if keys := os.environ.get("SOPS_AGE_KEY"):
        # SOPS_AGE_KEY is fed into age.ParseIdentities by Sops, and reads
        # identities line by line. See age/keysource.go in Sops, and
        # age/parse.go in Age.
        private_age_keys.extend(keys.strip().splitlines())

    def maybe_read_from_path(key_path: Path) -> None:
        try:
            contents = Path(key_path).read_text().strip()
            lines = contents.splitlines() # as in parse.go in age:
            private_age_keys.extend(l for l in lines if l and not l.startswith("#"))
        except FileNotFoundError:
            return
        except Exception as ex:
            log.warn(f"Could not read age keys from {key_path}: {ex}")

    # Sops will try every location, see age/keysource.go
    if key_path := os.environ.get("SOPS_AGE_KEY_FILE"):
        maybe_read_from_path(Path(key_path))
    maybe_read_from_path(user_config_dir() / "sops/age/keys.txt")

    return private_age_keys


def ensure_admin_public_key(flake_dir: Path) -> SopsKey:
    key = maybe_get_admin_public_key()
    if key:
        return ensure_user_or_machine(flake_dir, key)
    msg = "No sops key found. Please generate one with 'clan secrets key generate'."
    raise ClanError(msg)


def update_keys(secret_path: Path, keys: Iterable[tuple[str, KeyType]]) -> list[Path]:
    secret_path = secret_path / "secret"
    error_msg = f"Could not update keys for {secret_path}"
    executor = functools.partial(run, log=Log.BOTH, error_msg=error_msg)
    rc, _ = Operation.update_keys(secret_path, keys, executor)
    was_modified = ExitStatus.parse(rc) != ExitStatus.FILE_HAS_NOT_BEEN_MODIFIED
    return [secret_path] if was_modified else []


def encrypt_file(
    secret_path: Path,
    content: IO[str] | str | bytes | None,
    pubkeys: list[tuple[str, KeyType]],
) -> None:
    folder = secret_path.parent
    folder.mkdir(parents=True, exist_ok=True)

    if not content:
        # Don't use our `run` here, because it breaks editor integration.
        # We never need this in our UI.
        def executor(cmd: list[str], *, env: dict[str, str] | None = None) -> CmdOut:
            return CmdOut(
                stdout="",
                stderr="",
                cwd=Path.cwd(),
                env=env,
                command_list=cmd,
                returncode=subprocess.run(cmd, env=env, check=False).returncode,
                msg=None,
            )

        rc, _ = Operation.edit(secret_path, pubkeys, executor)
        status = ExitStatus.parse(rc)
        if rc == 0 or status == ExitStatus.FILE_HAS_NOT_BEEN_MODIFIED:
            return
        msg = f"Failed to encrypt {secret_path}: sops exited with {status or rc}"
        raise ClanError(msg)

    def swap_secret(f: Any) -> None:  # f's type is not exposed by tempfile
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
            Operation.encrypt(f.name, pubkeys, functools.partial(run, log=Log.BOTH))
            # atomic copy of the encrypted file
            with NamedTemporaryFile(dir=folder, delete=False) as f2:
                shutil.copyfile(f.name, f2.name)
                Path(f2.name).rename(secret_path)
        finally:
            with suppress(OSError):
                Path(f.name).unlink()

    try:
        with NamedTemporaryFile(dir="/dev/shm", delete=False) as f:
            swap_secret(f)
    except (FileNotFoundError, PermissionError):
        # hopefully /tmp is written to an in-memory file to avoid leaking secrets
        with NamedTemporaryFile(delete=False) as f:
            swap_secret(f)


def decrypt_file(secret_path: Path) -> str:
    # decryption uses private keys from the environment or default paths:
    no_public_keys_needed: list[tuple[str, KeyType]] = []
    executor = functools.partial(run, error_msg=f"Could not decrypt {secret_path}")
    _, stdout = Operation.decrypt(secret_path, no_public_keys_needed, executor)
    return stdout


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
