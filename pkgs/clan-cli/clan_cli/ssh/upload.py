import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from clan_cli.cmd import Log, RunOpts
from clan_cli.cmd import run as run_local
from clan_cli.errors import ClanError
from clan_cli.ssh.host import Host


def upload(
    host: Host,
    local_src: Path,  # must be a directory
    remote_dest: Path,  # must be a directory
    file_user: str = "root",
    file_group: str = "root",
    dir_mode: int = 0o700,
    file_mode: int = 0o400,
) -> None:
    # check if the remote destination is a directory (no suffix)
    if remote_dest.suffix:
        msg = "Only directories are allowed"
        raise ClanError(msg)

    if not local_src.is_dir():
        msg = "Only directories are allowed"
        raise ClanError(msg)

    # Create the tarball from the temporary directory
    with TemporaryDirectory(prefix="facts-upload-") as tardir:
        tar_path = Path(tardir) / "upload.tar.gz"
        # We set the permissions of the files and directories in the tarball to read only and owned by root
        # As first uploading the tarball and then changing the permissions can lead an attacker to
        # do a race condition attack
        with tarfile.open(str(tar_path), "w:gz") as tar:
            for root, dirs, files in local_src.walk():
                for mdir in dirs:
                    dir_path = Path(root) / mdir
                    tarinfo = tar.gettarinfo(
                        dir_path, arcname=str(dir_path.relative_to(str(local_src)))
                    )
                    tarinfo.mode = dir_mode
                    tarinfo.uname = file_user
                    tarinfo.gname = file_group
                    tar.addfile(tarinfo)
                for file in files:
                    file_path = Path(root) / file
                    tarinfo = tar.gettarinfo(
                        file_path,
                        arcname=str(file_path.relative_to(str(local_src))),
                    )
                    tarinfo.mode = file_mode
                    tarinfo.uname = file_user
                    tarinfo.gname = file_group
                    with file_path.open("rb") as f:
                        tar.addfile(tarinfo, f)

        cmd = [
            *host.ssh_cmd(),
            "rm",
            "-r",
            str(remote_dest),
            ";",
            "mkdir",
            f"--mode={dir_mode:o}",
            "-p",
            str(remote_dest),
            "&&",
            "tar",
            "-C",
            str(remote_dest),
            "-xzf",
            "-",
        ]

        # TODO accept `input` to be  an IO object instead of bytes so that we don't have to read the tarfile into memory.
        with tar_path.open("rb") as f:
            run_local(
                cmd,
                RunOpts(
                    input=f.read(),
                    log=Log.BOTH,
                    prefix=host.command_prefix,
                    needs_user_terminal=True,
                ),
            )
