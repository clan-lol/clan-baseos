import dataclasses
import enum
import io
import json
import logging
import os
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO

from clan_cli.api import API
from clan_cli.cmd import Log, RunOpts, run
from clan_cli.dirs import user_config_dir
from clan_cli.errors import ClanError
from clan_cli.nix import nix_shell

from .folders import sops_machines_folder, sops_users_folder

log = logging.getLogger(__name__)


class KeyType(enum.Enum):
    AGE = enum.auto()
    PGP = enum.auto()

    @classmethod
    def validate(cls, value: str | None) -> "KeyType | None":
        if value:
            return cls.__members__.get(value.upper())
        return None

    @property
    def sops_recipient_attr(self) -> str:
        """Name of the attribute to get the recipient key from a Sops file."""
        if self == self.AGE:
            return "recipient"
        if self == self.PGP:
            return "fp"
        msg = (
            f"KeyType is not properly implemented: "
            f'"sops_recipient_attr" is missing for key type "{self.name}"'
        )
        raise ClanError(msg)

    def collect_public_keys(self) -> Sequence[str]:
        keyring: list[str] = []

        if self == self.AGE:
            if keys := os.environ.get("SOPS_AGE_KEY"):
                # SOPS_AGE_KEY is fed into age.ParseIdentities by Sops, and
                # reads identities line by line. See age/keysource.go in
                # Sops, and age/parse.go in Age.
                for private_key in keys.strip().splitlines():
                    public_key = get_public_age_key(private_key)
                    log.info(
                        f"Found age public key from a private key "
                        f"in the environment (SOPS_AGE_KEY): {public_key}"
                    )
                    keyring.append(public_key)

            def maybe_read_from_path(key_path: Path) -> None:
                try:
                    # as in parse.go in age:
                    lines = Path(key_path).read_text().strip().splitlines()
                    for private_key in filter(lambda ln: not ln.startswith("#"), lines):
                        public_key = get_public_age_key(private_key)
                        log.info(
                            f"Found age public key from a private key "
                            f"in {key_path}: {public_key}"
                        )
                        keyring.append(public_key)
                except FileNotFoundError:
                    return
                except Exception as ex:
                    log.warning(f"Could not read age keys from {key_path}", exc_info=ex)

            # Sops will try every location, see age/keysource.go
            if key_path := os.environ.get("SOPS_AGE_KEY_FILE"):
                maybe_read_from_path(Path(key_path))
            maybe_read_from_path(user_config_dir() / "sops/age/keys.txt")

            return keyring

        if self == self.PGP:
            if pgp_fingerprints := os.environ.get("SOPS_PGP_FP"):
                for fp in pgp_fingerprints.strip().split(","):
                    msg = f"Found PGP public key in the environment (SOPS_PGP_FP): {fp}"
                    log.info(msg)
                    keyring.append(fp)
            return keyring

        msg = f"KeyType {self.name.lower()} is missing an implementation for collect_public_keys"
        raise ClanError(msg)


@dataclasses.dataclass(frozen=True)
class SopsKey:
    pubkey: str
    # Two SopsKey are considered equal even
    # if they don't have the same username:
    username: str = dataclasses.field(compare=False)
    key_type: KeyType

    def as_dict(self) -> dict[str, str]:
        return {
            "publickey": self.pubkey,
            "username": self.username,
            "type": self.key_type.name.lower(),
        }

    @classmethod
    def load_dir(cls, folder: Path) -> "SopsKey":
        """Load from the file named `keys.json` in the given directory."""
        pubkey, key_type = read_key(folder)
        username = ""
        return cls(pubkey, username, key_type)

    @classmethod
    def collect_public_keys(cls) -> Sequence["SopsKey"]:
        return [
            cls(pubkey=key, username="", key_type=key_type)
            for key_type in KeyType
            for key in key_type.collect_public_keys()
        ]


class ExitStatus(enum.IntEnum):  # see: cmd/sops/codes/codes.go
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
    def parse(cls, code: int) -> "ExitStatus | None":
        return ExitStatus(code) if code in ExitStatus else None


# class Executer(Protocol):
#     def __call__(
#         self, cmd: list[str], *, env: dict[str, str] | None = None
#     ) -> CmdOut: ...


class Operation(enum.StrEnum):
    DECRYPT = "decrypt"
    EDIT = "edit"
    ENCRYPT = "encrypt"
    UPDATE_KEYS = "updatekeys"


def sops_run(
    call: Operation,
    secret_path: Path,
    public_keys: Iterable[tuple[str, KeyType]],
    run_opts: RunOpts | None = None,
) -> tuple[int, str]:
    """Call the sops binary for the given operation."""
    # louis(2024-11-19): I regrouped the call into the sops binary into this
    # one place because calling into sops needs to be done with a carefully
    # setup context, and I don't feel good about the idea of having that logic
    # exist in multiple places.
    sops_cmd = ["sops"]
    environ = os.environ.copy()
    with NamedTemporaryFile(delete=False, mode="w") as manifest:
        if call == Operation.DECRYPT:
            sops_cmd.append("decrypt")
        else:
            # When sops is used to edit a file the config is only used at
            # file creation, otherwise the keys from the existing file are
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

            if call == Operation.ENCRYPT:
                # Remove SOPS env vars used to specify public keys to force
                # sops to use our config file [1]; so that the file gets
                # encrypted with our keys and not something leaking out of
                # the environment.
                #
                # [1]: https://github.com/getsops/sops/blob/8c567aa8a7cf4802e251e87efc84a1c50b69d4f0/cmd/sops/main.go#L2229
                for var in os.environ:
                    if var.startswith("SOPS_") and var not in {  # allowed:
                        "SOPS_GPG_EXEC",
                        "SOPS_AGE_KEY",
                        "SOPS_AGE_KEY_FILE",
                    }:
                        del environ[var]
                sops_cmd.extend(["encrypt", "--in-place"])
            elif call == Operation.UPDATE_KEYS:
                sops_cmd.extend(["updatekeys", "--yes"])
            elif call != Operation.EDIT:
                known_operations = ",".join(Operation.__members__.values())
                msg = (
                    f"Unsupported sops operation {call.value} "
                    f"(known operations: {known_operations})"
                )
                raise ClanError(msg)
        sops_cmd.append(str(secret_path))

        cmd = nix_shell(["nixpkgs#sops"], sops_cmd)
        opts = (
            dataclasses.replace(run_opts, env=environ)
            if run_opts
            else RunOpts(env=environ)
        )
        if call == Operation.EDIT:
            # Use direct stdout / stderr, as else it breaks editor integration.
            # We never need this in our UI. TUI only.
            p1 = subprocess.run(cmd, check=False, text=True)
            return p1.returncode, ""
        p = run(cmd, opts)
        return p.returncode, p.stdout


def get_public_age_key(privkey: str) -> str:
    cmd = nix_shell(["nixpkgs#age"], ["age-keygen", "-y"])

    error_msg = "Failed to get public key for age private key. Is the key malformed?"
    res = run(cmd, RunOpts(input=privkey.encode(), error_msg=error_msg))
    return res.stdout.rstrip(os.linesep).rstrip()


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
    keyring = SopsKey.collect_public_keys()
    if len(keyring) == 0:
        return None

    if len(keyring) > 1:
        last_3 = [f"{key.key_type.name.lower()}:{key.pubkey}" for key in keyring[:3]]
        msg = (
            f"Found {len(keyring)} public keys in your "
            f"environment/system and cannot decide which one to "
            f"use, first {len(last_3)}:\n\n"
            f"- {'\n- '.join(last_3)}\n\n"
            f"Please set one of SOPS_AGE_KEY, SOPS_AGE_KEY_FILE or "
            f"SOPS_PGP_FP appropriately"
        )
        raise ClanError(msg)

    return keyring[0]


def ensure_admin_public_key(flake_dir: Path) -> SopsKey:
    key = maybe_get_admin_public_key()
    if key:
        return ensure_user_or_machine(flake_dir, key)
    msg = "No sops key found. Please generate one with 'clan secrets key generate'."
    raise ClanError(msg)


def update_keys(secret_path: Path, keys: Iterable[tuple[str, KeyType]]) -> list[Path]:
    secret_path = secret_path / "secret"
    error_msg = f"Could not update keys for {secret_path}"

    rc, _ = sops_run(
        Operation.UPDATE_KEYS,
        secret_path,
        keys,
        RunOpts(log=Log.BOTH, error_msg=error_msg),
    )
    was_modified = ExitStatus.parse(rc) != ExitStatus.FILE_HAS_NOT_BEEN_MODIFIED
    return [secret_path] if was_modified else []


def encrypt_file(
    secret_path: Path,
    content: str | IO[bytes] | bytes | None,
    pubkeys: list[tuple[str, KeyType]],
) -> None:
    folder = secret_path.parent
    folder.mkdir(parents=True, exist_ok=True)

    if not content:
        # This will spawn an editor to edit the file.
        rc, _ = sops_run(
            Operation.EDIT,
            secret_path,
            pubkeys,
            RunOpts(),
        )
        status = ExitStatus.parse(rc)
        if rc == 0 or status == ExitStatus.FILE_HAS_NOT_BEEN_MODIFIED:
            return
        msg = f"Failed to encrypt {secret_path}: sops exited with {status or rc}"
        raise ClanError(msg)

    # lopter(2024-11-19): imo NamedTemporaryFile does RAII wrong since it
    # creates the file in __init__, when really it should be created in
    # __enter__ (that is in Python __enter__ is actually __init__ from a RAII
    # perspective, and __init__ should just be thought off as syntax sugar to
    # capture extra context), and now the linter is unhappy so hush it. Note
    # that if NamedTemporaryFile created the file in __enter__ then we'd have
    # to change exception handling:
    try:
        source = NamedTemporaryFile(dir="/dev/shm", delete=False)  # noqa: SIM115
    except (FileNotFoundError, PermissionError):
        source = NamedTemporaryFile(delete=False)  # noqa: SIM115
    try:  # swap the secret:
        with source:
            if isinstance(content, str):
                source.file.write(content.encode())
            elif isinstance(content, bytes):
                source.file.write(content)
            elif isinstance(content, io.BufferedReader):
                # lopter@(2024-11-19): mypy is freaking out on the 1st
                #                      argument, idk why, it says:
                #
                # > Cannot infer type argument 1 of "copyfileobj"
                shutil.copyfileobj(content, source.file)  # type: ignore[misc]
            else:
                msg = f"Invalid content type: {type(content)}"
                raise ClanError(msg)
        sops_run(
            Operation.ENCRYPT,
            Path(source.name),
            pubkeys,
            RunOpts(log=Log.BOTH),
        )
        # atomic copy of the encrypted file
        with NamedTemporaryFile(dir=folder, delete=False) as dest:
            shutil.copyfile(source.name, dest.name)
            Path(dest.name).rename(secret_path)
    finally:
        with suppress(OSError):
            Path(source.name).unlink()


def decrypt_file(secret_path: Path) -> str:
    # decryption uses private keys from the environment or default paths:
    no_public_keys_needed: list[tuple[str, KeyType]] = []

    _, stdout = sops_run(
        Operation.DECRYPT,
        secret_path,
        no_public_keys_needed,
        RunOpts(error_msg=f"Could not decrypt {secret_path}"),
    )
    return stdout


def get_recipients(secret_path: Path) -> set[SopsKey]:
    sops_attrs = json.loads((secret_path / "secret").read_text())["sops"]
    return {
        SopsKey(
            pubkey=recipient[key_type.sops_recipient_attr],
            username="",
            key_type=key_type,
        )
        for key_type in KeyType
        for recipient in sops_attrs[key_type.name.lower()] or []
    }


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
        msg = f'Invalid key type in {path.name}: "{key_type}" (expected one of {", ".join(KeyType.__members__.keys())}).'
        raise ClanError(msg)
    publickey = key.get("publickey")
    if not publickey:
        msg = f"{path.name} does not contain a public key"
        raise ClanError(msg)
    return publickey, key_type
