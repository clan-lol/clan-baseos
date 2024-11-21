# Adapted from https://github.com/numtide/deploykit

import fcntl
import math
import os
import select
import shlex
import subprocess
import tarfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from shlex import quote
from tempfile import TemporaryDirectory
from typing import IO, Any

from clan_cli.cmd import Log, terminate_process_group
from clan_cli.cmd import run as local_run
from clan_cli.errors import ClanError
from clan_cli.ssh.host_key import HostKeyCheck
from clan_cli.ssh.logger import cmdlog

FILE = None | int
# Seconds until a message is printed when _run produces no output.
NO_OUTPUT_TIMEOUT = 20


@contextmanager
def _pipe() -> Iterator[tuple[IO[str], IO[str]]]:
    (pipe_r, pipe_w) = os.pipe()
    read_end = os.fdopen(pipe_r, "r")
    write_end = os.fdopen(pipe_w, "w")

    try:
        fl = fcntl.fcntl(read_end, fcntl.F_GETFL)
        fcntl.fcntl(read_end, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        yield (read_end, write_end)
    finally:
        read_end.close()
        write_end.close()


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

    def _prefix_output(
        self,
        displayed_cmd: str,
        print_std_fd: IO[str] | None,
        print_err_fd: IO[str] | None,
        stdout: IO[str] | None,
        stderr: IO[str] | None,
        timeout: float = math.inf,
    ) -> tuple[str, str]:
        rlist = []
        if print_std_fd is not None:
            rlist.append(print_std_fd)
        if print_err_fd is not None:
            rlist.append(print_err_fd)
        if stdout is not None:
            rlist.append(stdout)

        if stderr is not None:
            rlist.append(stderr)

        print_std_buf = ""
        print_err_buf = ""
        stdout_buf = ""
        stderr_buf = ""

        start = time.time()
        last_output = time.time()
        while len(rlist) != 0:
            readlist, _, _ = select.select(
                rlist, [], [], min(timeout, NO_OUTPUT_TIMEOUT)
            )

            def print_from(
                print_fd: IO[str], print_buf: str, is_err: bool = False
            ) -> tuple[float, str]:
                read = os.read(print_fd.fileno(), 4096)
                if len(read) == 0:
                    rlist.remove(print_fd)
                print_buf += read.decode("utf-8")
                if (read == b"" and len(print_buf) != 0) or "\n" in print_buf:
                    # print and empty the print_buf, if the stream is draining,
                    # but there is still something in the buffer or on newline.
                    lines = print_buf.rstrip("\n").split("\n")
                    for line in lines:
                        if not is_err:
                            cmdlog.info(
                                line, extra={"command_prefix": self.command_prefix}
                            )
                        else:
                            cmdlog.error(
                                line, extra={"command_prefix": self.command_prefix}
                            )
                    print_buf = ""
                last_output = time.time()
                return (last_output, print_buf)

            if print_std_fd in readlist and print_std_fd is not None:
                (last_output, print_std_buf) = print_from(
                    print_std_fd, print_std_buf, is_err=False
                )
            if print_err_fd in readlist and print_err_fd is not None:
                (last_output, print_err_buf) = print_from(
                    print_err_fd, print_err_buf, is_err=True
                )

            now = time.time()
            elapsed = now - start
            if now - last_output > NO_OUTPUT_TIMEOUT:
                elapsed_msg = time.strftime("%H:%M:%S", time.gmtime(elapsed))
                cmdlog.warning(
                    f"still waiting for '{displayed_cmd}' to finish... ({elapsed_msg} elapsed)",
                    extra={"command_prefix": self.command_prefix},
                )

            def handle_fd(fd: IO[Any] | None, readlist: list[IO[Any]]) -> str:
                if fd and fd in readlist:
                    read = os.read(fd.fileno(), 4096)
                    if len(read) == 0:
                        rlist.remove(fd)
                    else:
                        return read.decode("utf-8")
                return ""

            stdout_buf += handle_fd(stdout, readlist)
            stderr_buf += handle_fd(stderr, readlist)

            if now - last_output >= timeout:
                break
        return stdout_buf, stderr_buf

    def _run(
        self,
        cmd: list[str],
        displayed_cmd: str,
        shell: bool,
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        needs_user_terminal: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if extra_env is None:
            extra_env = {}
        with ExitStack() as stack:
            read_std_fd, write_std_fd = (None, None)
            read_err_fd, write_err_fd = (None, None)

            if stdout is None or stderr is None:
                read_std_fd, write_std_fd = stack.enter_context(_pipe())
                read_err_fd, write_err_fd = stack.enter_context(_pipe())

            if stdout is None:
                stdout_read = None
                stdout_write = write_std_fd
            elif stdout == subprocess.PIPE:
                stdout_read, stdout_write = stack.enter_context(_pipe())
            else:
                msg = f"unsupported value for stdout parameter: {stdout}"
                raise ClanError(msg)

            if stderr is None:
                stderr_read = None
                stderr_write = write_err_fd
            elif stderr == subprocess.PIPE:
                stderr_read, stderr_write = stack.enter_context(_pipe())
            else:
                msg = f"unsupported value for stderr parameter: {stderr}"
                raise ClanError(msg)

            env = os.environ.copy()
            env.update(extra_env)

            with subprocess.Popen(
                cmd,
                text=True,
                shell=shell,
                stdout=stdout_write,
                stderr=stderr_write,
                env=env,
                cwd=cwd,
                start_new_session=not needs_user_terminal,
            ) as p:
                if not needs_user_terminal:
                    stack.enter_context(terminate_process_group(p))
                if write_std_fd is not None:
                    write_std_fd.close()
                if write_err_fd is not None:
                    write_err_fd.close()
                if stdout == subprocess.PIPE:
                    assert stdout_write is not None
                    stdout_write.close()
                if stderr == subprocess.PIPE:
                    assert stderr_write is not None
                    stderr_write.close()

                start = time.time()
                stdout_data, stderr_data = self._prefix_output(
                    displayed_cmd,
                    read_std_fd,
                    read_err_fd,
                    stdout_read,
                    stderr_read,
                    timeout,
                )
                ret = p.wait(timeout=max(0, timeout - (time.time() - start)))
                if ret != 0:
                    if check:
                        msg = f"Command {shlex.join(cmd)} failed with return code {ret}"
                        raise ClanError(msg)
                    cmdlog.warning(
                        f"[Command failed: {ret}] {displayed_cmd}",
                        extra={"command_prefix": self.command_prefix},
                    )
                return subprocess.CompletedProcess(
                    cmd, ret, stdout=stdout_data, stderr=stderr_data
                )
        msg = "unreachable"
        raise RuntimeError(msg)

    def run_local(
        self,
        cmd: str | list[str],
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
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
        if extra_env is None:
            extra_env = {}
        shell = False
        if isinstance(cmd, str):
            cmd = [cmd]
            shell = True
        displayed_cmd = " ".join(cmd)
        cmdlog.info(f"$ {displayed_cmd}", extra={"command_prefix": self.command_prefix})
        return self._run(
            cmd,
            displayed_cmd,
            shell=shell,
            stdout=stdout,
            stderr=stderr,
            extra_env=extra_env,
            cwd=cwd,
            check=check,
            timeout=timeout,
        )

    def run(
        self,
        cmd: str | list[str],
        stdout: FILE = None,
        stderr: FILE = None,
        become_root: bool = False,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        verbose_ssh: bool = False,
        tty: bool = False,
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
        sudo = ""
        if become_root and self.user != "root":
            sudo = "sudo -- "
        env_vars = []
        for k, v in extra_env.items():
            env_vars.append(f"{shlex.quote(k)}={shlex.quote(v)}")

        displayed_cmd = ""
        export_cmd = ""
        if env_vars:
            export_cmd = f"export {' '.join(env_vars)}; "
            displayed_cmd += export_cmd
        if isinstance(cmd, list):
            displayed_cmd += " ".join(cmd)
        else:
            displayed_cmd += cmd
        cmdlog.info(f"$ {displayed_cmd}", extra={"command_prefix": self.command_prefix})

        bash_cmd = export_cmd
        bash_args = []
        if isinstance(cmd, list):
            bash_cmd += 'exec "$@"'
            bash_args += cmd
        else:
            bash_cmd += cmd
        # FIXME we assume bash to be present here? Should be documented...
        ssh_cmd = [
            *self.ssh_cmd(verbose_ssh=verbose_ssh, tty=tty),
            "--",
            f"{sudo}bash -c {quote(bash_cmd)} -- {' '.join(map(quote, bash_args))}",
        ]
        return self._run(
            ssh_cmd,
            displayed_cmd,
            shell=False,
            stdout=stdout,
            stderr=stderr,
            cwd=cwd,
            check=check,
            timeout=timeout,
            # all ssh commands can potentially ask for a password
            needs_user_terminal=True,
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
                "-xvzf",
                "-",
            ]

            # TODO accept `input` to be  an IO object instead of bytes so that we don't have to read the tarfile into memory.
            with tar_path.open("rb") as f:
                local_run(cmd, input=f.read(), log=Log.BOTH, needs_user_terminal=True)

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
