# Adapted from https://github.com/numtide/deploykit

import logging
import math
import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from shlex import quote
from typing import IO, Any

from clan_cli.cmd import CmdOut, Log, MsgColor, RunOpts, run
from clan_cli.colors import AnsiColor
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

    @property
    def target(self) -> str:
        return f"{self.user or 'root'}@{self.host}"

    @property
    def target_for_rsync(self) -> str:
        host = self.host
        if ":" in host:
            host = f"[{host}]"
        return f"{self.user or 'root'}@{host}"

    def run_local(
        self,
        cmd: list[str],
        opts: RunOpts | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> CmdOut:
        """
        Command to run locally for the host
        """
        if opts is None:
            opts = RunOpts()
        env = opts.env or os.environ.copy()
        if extra_env:
            env.update(extra_env)

        displayed_cmd = " ".join(cmd)
        cmdlog.info(
            f"$ {displayed_cmd}",
            extra={
                "command_prefix": self.command_prefix,
                "color": AnsiColor.GREEN.value,
            },
        )
        opts.env = env
        opts.prefix = self.command_prefix
        return run(cmd, opts)

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
        msg_color: MsgColor | None = None,
        shell: bool = False,
        log: Log = Log.BOTH,
    ) -> CmdOut:
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
        cmdlog.info(
            f"$ {displayed_cmd}",
            extra={
                "command_prefix": self.command_prefix,
                "color": AnsiColor.GREEN.value,
            },
        )

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

        opts = RunOpts(
            shell=False,
            stdout=stdout,
            stderr=stderr,
            log=log,
            cwd=cwd,
            check=check,
            prefix=self.command_prefix,
            timeout=timeout,
            msg_color=msg_color,
            needs_user_terminal=True,  # ssh asks for a password
        )

        # Run the ssh command
        return run(ssh_cmd, opts)

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
