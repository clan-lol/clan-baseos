import subprocess
import tempfile
from pathlib import Path

import pytest
from clan_cli import git
from clan_cli.errors import ClanError


def test_commit_file(git_repo: Path) -> None:
    # create a file in the git repo
    (git_repo / "test.txt").touch()
    # commit the file
    git.commit_file((git_repo / "test.txt"), git_repo, "test commit")
    # check that the repo directory does in fact contain the file
    assert (git_repo / "test.txt").exists()
    # check that the working tree is clean
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=git_repo)
    # check that the latest commit message is correct
    assert (
        subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"], cwd=git_repo
        ).decode("utf-8")
        == "test commit\n\n"
    )


def test_commit_file_outside_git_raises_error(git_repo: Path) -> None:
    # create a file outside the git (a temporary file)
    with tempfile.NamedTemporaryFile() as tmp, pytest.raises(ClanError):
        # this should not fail but skip the commit
        git.commit_file(Path(tmp.name), git_repo, "test commit")


def test_commit_file_not_existing_raises_error(git_repo: Path) -> None:
    # commit a file that does not exist
    with pytest.raises(ClanError):
        git.commit_file(Path("test.txt"), git_repo, "test commit")


def test_clan_flake_in_subdir(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # create a clan_flake subdirectory
    (git_repo / "clan_flake").mkdir()
    # create a .clan-flake file
    (git_repo / "clan_flake" / ".clan-flake").touch()
    # change to the clan_flake subdirectory
    monkeypatch.chdir(git_repo / "clan_flake")
    # commit files to git
    subprocess.run(["git", "add", "."], cwd=git_repo)
    subprocess.run(["git", "commit", "-m", "init"], cwd=git_repo)
    # add a new file under ./clan_flake
    (git_repo / "clan_flake" / "test.txt").touch()
    # commit the file
    git.commit_file(git_repo / "clan_flake" / "test.txt", git_repo, "test commit")
    # check that the repo directory does in fact contain the file
    assert (git_repo / "clan_flake" / "test.txt").exists()
    # check that the working tree is clean
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=git_repo)
    # check that the latest commit message is correct
    assert (
        subprocess.check_output(
            ["git", "log", "-1", "--pretty=%B"], cwd=git_repo
        ).decode("utf-8")
        == "test commit\n\n"
    )
