from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from clan_cli.custom_logger import setup_logging
from clan_cli.nix import nix_shell

pytest_plugins = [
    "temporary_dir",
    "root",
    "command",
    "wayland",
]


# Executed on pytest session start
def pytest_sessionstart(session: pytest.Session) -> None:
    # This function will be called once at the beginning of the test session
    print("Starting pytest session")
    # You can access the session config, items, testsfailed, etc.
    print(f"Session config: {session.config}")

    setup_logging(level="DEBUG")


# fixture for git_repo
@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    # initialize a git repository
    cmd = nix_shell(["nixpkgs#git"], ["git", "init"])
    subprocess.run(cmd, cwd=tmp_path, check=True)
    # set user.name and user.email
    cmd = nix_shell(["nixpkgs#git"], ["git", "config", "user.name", "test"])
    subprocess.run(cmd, cwd=tmp_path, check=True)
    cmd = nix_shell(["nixpkgs#git"], ["git", "config", "user.email", "test@test.test"])
    subprocess.run(cmd, cwd=tmp_path, check=True)
    # return the path to the git repository
    return tmp_path
