from pathlib import Path

from clan_cli.dirs import specific_machine_dir


def machine_has_fact(flake_dir: Path, machine: str, fact: str) -> bool:
    return (specific_machine_dir(flake_dir, machine) / "facts" / fact).exists()


def machine_get_fact(flake_dir: Path, machine: str, fact: str) -> str:
    return (specific_machine_dir(flake_dir, machine) / "facts" / fact).read_text()
