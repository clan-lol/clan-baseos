from pathlib import Path

from .cmd import Log, RunOpts, run
from .errors import ClanError
from .locked_open import locked_open
from .nix import run_cmd


def commit_file(
    file_path: Path,
    repo_dir: Path,
    commit_message: str | None = None,
) -> None:
    """Commit a file to a git repository.

    :param file_path: The path to the file to commit.
    :param repo_dir: The path to the git repository.
    :param commit_message: The commit message.
    :raises ClanError: If the file is not in the git repository.
    """
    commit_files([file_path], repo_dir, commit_message)


# generic vcs agnostic commit function
def commit_files(
    file_paths: list[Path],
    repo_dir: Path,
    commit_message: str | None = None,
) -> None:
    if not file_paths:
        return
    # check that the file is in the git repository
    for file_path in file_paths:
        if not Path(file_path).resolve().is_relative_to(repo_dir.resolve()):
            msg = f"File {file_path} is not in the git repository {repo_dir}"
            raise ClanError(msg)
    # generate commit message if not provided
    if commit_message is None:
        commit_message = ""
        for file_path in file_paths:
            # ensure that mentioned file path is relative to repo
            commit_message += f"Add {file_path.relative_to(repo_dir)}"
    # check if the repo is a git repo and commit
    if (repo_dir / ".git").exists():
        _commit_file_to_git(repo_dir, file_paths, commit_message)
    else:
        return


def _commit_file_to_git(
    repo_dir: Path, file_paths: list[Path], commit_message: str
) -> None:
    """Commit a file to a git repository.

    :param repo_dir: The path to the git repository.
    :param file_path: The path to the file to commit.
    :param commit_message: The commit message.
    :raises ClanError: If the file is not in the git repository.
    """
    dotgit = repo_dir / ".git"
    real_git_dir = repo_dir / ".git"
    # resolve worktree
    if dotgit.is_file():
        actual_git_dir = dotgit.read_text().strip()
        if not actual_git_dir.startswith("gitdir: "):
            msg = f"Invalid .git file: {actual_git_dir}"
            raise ClanError(msg)
        real_git_dir = repo_dir / actual_git_dir[len("gitdir: ") :]

    with locked_open(real_git_dir / "clan.lock", "w+"):
        for file_path in file_paths:
            cmd = run_cmd(
                ["git"],
                ["git", "-C", str(repo_dir), "add", "--", str(file_path)],
            )
            # add the file to the git index

            run(
                cmd,
                RunOpts(
                    log=Log.BOTH,
                    error_msg=f"Failed to add {file_path} file to git index",
                ),
            )

        # check if there is a diff
        cmd = run_cmd(
            ["git"],
            ["git", "-C", str(repo_dir), "diff", "--cached", "--exit-code", "--"]
            + [str(file_path) for file_path in file_paths],
        )
        result = run(cmd, RunOpts(check=False, cwd=repo_dir))
        # if there is no diff, return
        if result.returncode == 0:
            return

        # commit only that file
        cmd = run_cmd(
            ["git"],
            [
                "git",
                "-C",
                str(repo_dir),
                "commit",
                "-m",
                commit_message,
                "--no-verify",  # dont run pre-commit hooks
            ]
            + [str(file_path) for file_path in file_paths],
        )

        run(
            cmd,
            RunOpts(
                error_msg=f"Failed to commit {file_paths} to git repository {repo_dir}"
            ),
        )
