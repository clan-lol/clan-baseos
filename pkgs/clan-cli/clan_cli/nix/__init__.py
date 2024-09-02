import json
import os
import tempfile
from pathlib import Path
from typing import Any

from clan_cli.cmd import run, run_no_stdout
from clan_cli.dirs import nixpkgs_flake, nixpkgs_source


def nix_command(flags: list[str]) -> list[str]:
    return ["nix", "--extra-experimental-features", "nix-command flakes", *flags]


def nix_flake_show(flake_url: str | Path) -> list[str]:
    return nix_command(
        [
            "flake",
            "show",
            "--json",
            "--show-trace",
            "--no-write-lock-file",
            f"{flake_url}",
        ]
    )


def nix_build(flags: list[str], gcroot: Path | None = None) -> list[str]:
    if gcroot is not None:
        return (
            nix_command(
                [
                    "build",
                    "--out-link",
                    str(gcroot),
                    "--print-out-paths",
                    "--no-write-lock-file",
                    "--show-trace",
                ]
            )
            + flags
        )
    else:
        return (
            nix_command(
                [
                    "build",
                    "--no-link",
                    "--print-out-paths",
                    "--no-write-lock-file",
                    "--show-trace",
                ]
            )
            + flags
        )


def nix_add_to_gcroots(nix_path: Path, dest: Path) -> None:
    cmd = ["nix-store", "--realise", f"{nix_path}", "--add-root", f"{dest}"]
    run(cmd)


def nix_config() -> dict[str, Any]:
    cmd = nix_command(["show-config", "--json"])
    proc = run_no_stdout(cmd)
    data = json.loads(proc.stdout)
    config = {}
    for key, value in data.items():
        config[key] = value["value"]
    return config


def nix_eval(flags: list[str]) -> list[str]:
    default_flags = nix_command(
        [
            "eval",
            "--show-trace",
            "--json",
            "--no-write-lock-file",
        ]
    )
    if os.environ.get("IN_NIX_SANDBOX"):
        with tempfile.TemporaryDirectory() as nix_store:
            return [
                *default_flags,
                "--override-input",
                "nixpkgs",
                str(nixpkgs_source()),
                # --store is required to prevent this error:
                # error: cannot unlink '/nix/store/6xg259477c90a229xwmb53pdfkn6ig3g-default-builder.sh': Operation not permitted
                "--store",
                nix_store,
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
    if os.environ.get("IN_NIX_SANDBOX") or os.environ.get("CLAN_NO_DYNAMIC_DEPS"):
        return cmd
    return [
        *nix_command(["shell", "--inputs-from", f"{nixpkgs_flake()!s}"]),
        *packages,
        "-c",
        *cmd,
    ]


# lazy loads list of allowed and static programs
class Programs:
    allowed_programs = None
    static_programs = None

    @classmethod
    def is_allowed(cls: type["Programs"], program: str) -> bool:
        if cls.allowed_programs is None:
            with open(Path(__file__).parent / "allowed-programs.json") as f:
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
            raise ValueError(f"Program not allowed: {program}")
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
