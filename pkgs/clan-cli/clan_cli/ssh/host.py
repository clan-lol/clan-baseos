# Adapted from https://github.com/numtide/deploykit

import logging
import os
import shlex
import socket
import subprocess
from dataclasses import dataclass, field
from shlex import quote
from typing import Any

from clan_cli.cmd import CmdOut, RunOpts, run
from clan_cli.colors import AnsiColor
from clan_cli.errors import ClanError
from clan_cli.nix import nix_shell
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

    def __str__(self) -> str:
        return self.target

    @property
    def target(self) -> str:
        return f"{self.user or 'root'}@{self.host}"

    @classmethod
    def from_host(cls, host: "Host") -> "Host":
        return cls(
            host=host.host,
            user=host.user,
            port=host.port,
            key=host.key,
            forward_agent=host.forward_agent,
            command_prefix=host.command_prefix,
            host_key_check=host.host_key_check,
            meta=host.meta.copy(),
            verbose_ssh=host.verbose_ssh,
            ssh_options=host.ssh_options.copy(),
        )

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
        opts: RunOpts | None = None,
        become_root: bool = False,
        extra_env: dict[str, str] | None = None,
        tty: bool = False,
        verbose_ssh: bool = False,
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

        if opts is None:
            opts = RunOpts()
        else:
            opts.needs_user_terminal = True
            opts.prefix = self.command_prefix

        if opts.cwd is not None:
            msg = "cwd is not supported for remote commands"
            raise ClanError(msg)

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
        if opts.shell:
            bash_cmd += " ".join(cmd)
            opts.shell = False
        else:
            bash_cmd += 'exec "$@"'
        # FIXME we assume bash to be present here? Should be documented...
        ssh_cmd = [
            *self.ssh_cmd(verbose_ssh=verbose_ssh, tty=tty),
            "--",
            f"{sudo}bash -c {quote(bash_cmd)} -- {' '.join(map(quote, cmd))}",
        ]

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
        tor_socks: bool = False,
        tty: bool = False,
        password: str | None = None,
    ) -> list[str]:
        packages = []
        password_args = []
        if password:
            packages.append("nixpkgs#sshpass")
            password_args = [
                "sshpass",
                "-p",
                password,
            ]

        ssh_opts = self.ssh_cmd_opts
        if verbose_ssh or self.verbose_ssh:
            ssh_opts.extend(["-v"])
        if tty:
            ssh_opts.extend(["-t"])

        if self.port:
            ssh_opts.extend(["-p", str(self.port)])
        if self.key:
            ssh_opts.extend(["-i", self.key])

        if tor_socks:
            packages.append("nixpkgs#netcat")
            ssh_opts.append("-o")
            ssh_opts.append("ProxyCommand=nc -x 127.0.0.1:9050 -X 5 %h %p")

        cmd = [
            *password_args,
            "ssh",
            self.target,
            *ssh_opts,
        ]

        return nix_shell(packages, cmd)

    def connect_ssh_shell(
        self, *, password: str | None = None, tor_socks: bool = False
    ) -> None:
        cmd = self.ssh_cmd(tor_socks=tor_socks, password=password)

        subprocess.run(cmd)


def is_ssh_reachable(host: Host) -> bool:
    with socket.socket(
        socket.AF_INET6 if ":" in host.host else socket.AF_INET, socket.SOCK_STREAM
    ) as sock:
        sock.settimeout(2)
        try:
            sock.connect((host.host, host.port or 22))
            sock.close()
        except OSError:
            return False
        else:
            return True
