# Adapted from https://github.com/numtide/deploykit

import logging
import math
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from shlex import quote
from typing import IO, Any

from clan_cli.cmd import Log
from clan_cli.cmd import run as local_run
from clan_cli.ssh.host_key import HostKeyCheck

cmdlog = logging.getLogger(__name__)


# Seconds until a message is printed when _run produces no output.
NO_OUTPUT_TIMEOUT = 20


@dataclass
class Host:
    host: str
    user: str | None = None
    port: int | None = None
    key: str | None = None
    forward_agent: bool = False
    command_prefix: str | None = None
    host_key_check: HostKeyCheck = HostKeyCheck.ASK
    meta: dict[str, Any] = field(default_factory=dict)
    verbose_ssh: bool = False
    ssh_options: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.command_prefix:
            self.command_prefix = self.host

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
        needs_user_terminal: bool = False,
        log: Log = Log.BOTH,
    ) -> subprocess.CompletedProcess[str]:
        """
        Command to run locally for the host
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
            needs_user_terminal=needs_user_terminal,
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

    @property
    def ssh_cmd_opts(
        self,
    ) -> list[str]:
        ssh_opts = ["-A"] if self.forward_agent else []

        for k, v in self.ssh_options.items():
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
