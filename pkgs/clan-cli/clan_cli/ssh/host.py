# Adapted from https://github.com/numtide/deploykit

import logging
import math
import os
import shlex
import subprocess
import tarfile
from pathlib import Path
from shlex import quote
from tempfile import TemporaryDirectory
from typing import IO, Any

from clan_cli.cmd import Log
from clan_cli.cmd import run as local_run
from clan_cli.errors import ClanError
from clan_cli.ssh.host_key import HostKeyCheck

cmdlog = logging.getLogger(__name__)


# Seconds until a message is printed when _run produces no output.
NO_OUTPUT_TIMEOUT = 20


class Host:
    def __init__(
        self,
        host: str,
        user: str | None = None,
        port: int | None = None,
        key: str | None = None,
        forward_agent: bool = False,
        command_prefix: str | None = None,
        host_key_check: HostKeyCheck = HostKeyCheck.ASK,
        meta: dict[str, Any] | None = None,
        verbose_ssh: bool = False,
        ssh_options: dict[str, str] | None = None,
    ) -> None:
        """
        Creates a Host
        @host the hostname to connect to via ssh
        @port the port to connect to via ssh
        @forward_agent: whether to forward ssh agent
        @command_prefix: string to prefix each line of the command output with, defaults to host
        @host_key_check: whether to check ssh host keys
        @verbose_ssh: Enables verbose logging on ssh connections
        @meta: meta attributes associated with the host. Those can be accessed in custom functions passed to `run_function`
        """
        if ssh_options is None:
            ssh_options = {}
        if meta is None:
            meta = {}
        self.host = host
        self.user = user
        self.port = port
        self.key = key
        if command_prefix:
            self.command_prefix = command_prefix
        else:
            self.command_prefix = host
        self.forward_agent = forward_agent
        self.host_key_check = host_key_check
        self.meta = meta
        self.verbose_ssh = verbose_ssh
        self._ssh_options = ssh_options

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.user}@{self.host}" + str(self.port if self.port else "")

    @property
    def target(self) -> str:
        return f"{self.user or 'root'}@{self.host}"

    @property
    def target_for_rsync(self) -> str:
        host = self.host
        if ":" in host:
            host = f"[{host}]"
        return f"{self.user or 'root'}@{host}"

    def _run(
        self,
        cmd: list[str],
        *,
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        input: bytes | None = None,  # noqa: A002
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
        log: Log = Log.BOTH,
        check: bool = True,
        error_msg: str | None = None,
        needs_user_terminal: bool = False,
        shell: bool = False,
        timeout: float = math.inf,
    ) -> subprocess.CompletedProcess[str]:
        res = local_run(
            cmd,
            shell=shell,
            stdout=stdout,
            prefix=self.command_prefix,
            timeout=timeout,
            stderr=stderr,
            input=input,
            env=env,
            cwd=cwd,
            log=log,
            logger=cmdlog,
            check=check,
            error_msg=error_msg,
            needs_user_terminal=needs_user_terminal,
        )
        return subprocess.CompletedProcess(
            args=res.command_list,
            returncode=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
        )

    def run_local(
        self,
        cmd: list[str],
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        shell: bool = False,
        log: Log = Log.BOTH,
    ) -> subprocess.CompletedProcess[str]:
        """
        Command to run locally for the host

        @cmd the command to run
        @stdout if not None stdout of the command will be redirected to this file i.e. stdout=subprocess.PIPE
        @stderr if not None stderr of the command will be redirected to this file i.e. stderr=subprocess.PIPE
        @extra_env environment variables to override when running the command
        @cwd current working directory to run the process in
        @timeout: Timeout in seconds for the command to complete

        @return subprocess.CompletedProcess result of the command
        """
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)

        displayed_cmd = " ".join(cmd)
        cmdlog.info(f"$ {displayed_cmd}", extra={"command_prefix": self.command_prefix})
        return self._run(
            cmd,
            shell=shell,
            stdout=stdout,
            stderr=stderr,
            env=env,
            cwd=cwd,
            check=check,
            timeout=timeout,
            log=log,
        )

    def run(
        self,
        cmd: list[str],
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        become_root: bool = False,
        extra_env: dict[str, str] | None = None,
        cwd: None | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        verbose_ssh: bool = False,
        tty: bool = False,
        shell: bool = False,
        log: Log = Log.BOTH,
    ) -> subprocess.CompletedProcess[str]:
        """
        Command to run on the host via ssh

        @cmd the command to run
        @stdout if not None stdout of the command will be redirected to this file i.e. stdout=subprocss.PIPE
        @stderr if not None stderr of the command will be redirected to this file i.e. stderr=subprocess.PIPE
        @become_root if the ssh_user is not root than sudo is prepended
        @extra_env environment variables to override when running the command
        @cwd current working directory to run the process in
        @verbose_ssh: Enables verbose logging on ssh connections
        @timeout: Timeout in seconds for the command to complete

        @return subprocess.CompletedProcess result of the ssh command
        """
        if extra_env is None:
            extra_env = {}

        # If we are not root and we need to become root, prepend sudo
        sudo = ""
        if become_root and self.user != "root":
            sudo = "sudo -- "

        # Quote all added environment variables
        env_vars = []
        for k, v in extra_env.items():
            env_vars.append(f"{shlex.quote(k)}={shlex.quote(v)}")

        # Build a pretty command for logging
        displayed_cmd = ""
        export_cmd = ""
        if env_vars:
            export_cmd = f"export {' '.join(env_vars)}; "
            displayed_cmd += export_cmd
        displayed_cmd += " ".join(cmd)
        cmdlog.info(f"$ {displayed_cmd}", extra={"command_prefix": self.command_prefix})

        # Build the ssh command
        bash_cmd = export_cmd
        if shell:
            bash_cmd += " ".join(cmd)
        else:
            bash_cmd += 'exec "$@"'
        # FIXME we assume bash to be present here? Should be documented...
        ssh_cmd = [
            *self.ssh_cmd(verbose_ssh=verbose_ssh, tty=tty),
            "--",
            f"{sudo}bash -c {quote(bash_cmd)} -- {' '.join(map(quote, cmd))}",
        ]

        # Run the ssh command
        return self._run(
            ssh_cmd,
            shell=False,
            stdout=stdout,
            stderr=stderr,
            log=log,
            cwd=cwd,
            check=check,
            timeout=timeout,
            needs_user_terminal=True,  # ssh asks for a password
        )

    def nix_ssh_env(self, env: dict[str, str] | None) -> dict[str, str]:
        if env is None:
            env = {}
        env["NIX_SSHOPTS"] = " ".join(self.ssh_cmd_opts)
        return env

    def upload(
        self,
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
                *self.ssh_cmd(),
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
                local_run(
                    cmd,
                    input=f.read(),
                    log=Log.BOTH,
                    needs_user_terminal=True,
                    prefix=self.command_prefix,
                )

    @property
    def ssh_cmd_opts(
        self,
    ) -> list[str]:
        ssh_opts = ["-A"] if self.forward_agent else []

        for k, v in self._ssh_options.items():
            ssh_opts.extend(["-o", f"{k}={shlex.quote(v)}"])

        ssh_opts.extend(self.host_key_check.to_ssh_opt())

        return ssh_opts

    def ssh_cmd(
        self,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> list[str]:
        ssh_opts = self.ssh_cmd_opts
        if verbose_ssh or self.verbose_ssh:
            ssh_opts.extend(["-v"])
        if tty:
            ssh_opts.extend(["-t"])

        if self.port:
            ssh_opts.extend(["-p", str(self.port)])
        if self.key:
            ssh_opts.extend(["-i", self.key])

        return [
            "ssh",
            self.target,
            *ssh_opts,
        ]
