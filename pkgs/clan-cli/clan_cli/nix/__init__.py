import json
import logging
import os
from pathlib import Path
from typing import Any

from clan_cli.cmd import run, run_no_stdout
from clan_cli.dirs import nixpkgs_flake, nixpkgs_source
from clan_cli.errors import ClanError
from clan_cli.locked_open import locked_open

log = logging.getLogger(__name__)


def nix_command(flags: list[str]) -> list[str]:
    args = ["nix", "--extra-experimental-features", "nix-command flakes", *flags]
    if store := nix_test_store():
        args += ["--store", str(store)]
    return args


def nix_flake_show(flake_url: str | Path) -> list[str]:
    return nix_command(
        [
            "flake",
            "show",
            "--json",
            *(["--show-trace"] if log.isEnabledFor(logging.DEBUG) else []),
            str(flake_url),
        ]
    )


def nix_build(flags: list[str], gcroot: Path | None = None) -> list[str]:
    return nix_command(
        [
            "build",
            "--print-out-paths",
            "--print-build-logs",
            *(["--show-trace"] if log.isEnabledFor(logging.DEBUG) else []),
            *(["--out-root", str(gcroot)] if gcroot is not None else ["--no-link"]),
            *flags,
        ]
    )


def nix_add_to_gcroots(nix_path: Path, dest: Path) -> None:
    if not os.environ.get("IN_NIX_SANDBOX"):
        cmd = ["nix-store", "--realise", f"{nix_path}", "--add-root", f"{dest}"]
        run(cmd)


def nix_config() -> dict[str, Any]:
    cmd = nix_command(["config", "show", "--json"])
    proc = run_no_stdout(cmd)
    data = json.loads(proc.stdout)
    config = {}
    for key, value in data.items():
        config[key] = value["value"]
    return config


def nix_test_store() -> Path | None:
    store = os.environ.get("CLAN_TEST_STORE", None)
    if not os.environ.get("IN_NIX_SANDBOX"):
        return None
    if store:
        Path.mkdir(Path(store), exist_ok=True)
        with locked_open(filename=Path(store) / "lockfile", mode="a"):
            return Path(store)
    return None


def nix_eval(flags: list[str]) -> list[str]:
    default_flags = nix_command(
        [
            "eval",
            *(["--show-trace"] if log.isEnabledFor(logging.DEBUG) else []),
            "--json",
            "--print-build-logs",
        ]
    )
    if os.environ.get("IN_NIX_SANDBOX"):
        return [
            *default_flags,
            "--override-input",
            "nixpkgs",
            str(nixpkgs_source()),
            *flags,
        ]
    return default_flags + flags


def nix_metadata(flake_url: str | Path) -> dict[str, Any]:
    cmd = nix_command(["flake", "metadata", "--json", f"{flake_url}"])
    proc = run(cmd)
    data = json.loads(proc.stdout)
    return data


def nix_shell(packages: list[str], cmd: list[str]) -> list[str]:
    # we cannot use nix-shell inside the nix sandbox
    # in our tests we just make sure we have all the packages
    if (
        os.environ.get("IN_NIX_SANDBOX")
        or os.environ.get("CLAN_NO_DYNAMIC_DEPS")
        or len(packages) == 0
    ):
        return cmd
    return [
        *nix_command(["shell", "--inputs-from", f"{nixpkgs_flake()!s}"]),
        *packages,
        "-c",
        *cmd,
    ]


# lazy loads list of allowed and static programs
class Programs:
    allowed_programs: list[str] | None = None
    static_programs: list[str] | None = None

    @classmethod
    def is_allowed(cls: type["Programs"], program: str) -> bool:
        if cls.allowed_programs is None:
            with (Path(__file__).parent / "allowed-programs.json").open() as f:
                cls.allowed_programs = json.load(f)
        return program in cls.allowed_programs

    @classmethod
    def is_static(cls: type["Programs"], program: str) -> bool:
        """
        Determines if a program is statically shipped with this clan distribution
        """
        if cls.static_programs is None:
            cls.static_programs = os.environ.get("CLAN_STATIC_PROGRAMS", "").split(":")
        return program in cls.static_programs


# Alternative implementation of nix_shell() to replace nix_shell() at some point
#   Features:
#     - allow list for programs (need to be specified in allowed-programs.json)
#     - be abe to compute a closure of all deps for testing
#     - build clan distributions that ship some or all packages (eg. clan-cli-full)
def run_cmd(programs: list[str], cmd: list[str]) -> list[str]:
    for program in programs:
        if not Programs.is_allowed(program):
            msg = f"Program not allowed: {program}"
            raise ClanError(msg)
    if os.environ.get("IN_NIX_SANDBOX"):
        return cmd
    missing_packages = [
        f"nixpkgs#{program}" for program in programs if not Programs.is_static(program)
    ]
    if not missing_packages:
        return cmd
    return [
        *nix_command(["shell", "--inputs-from", f"{nixpkgs_flake()!s}"]),
        *missing_packages,
        "-c",
        *cmd,
    ]
