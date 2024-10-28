# Adapted from https://github.com/numtide/deploykit

import fcntl
import logging
import math
import os
import select
import shlex
import subprocess
import sys
import time
import urllib.parse
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from enum import Enum
from pathlib import Path
from shlex import quote
from threading import Thread
from typing import IO, Any, Generic, TypeVar

from clan_cli.cmd import terminate_process_group
from clan_cli.errors import ClanError

# https://no-color.org
DISABLE_COLOR = not sys.stderr.isatty() or os.environ.get("NO_COLOR", "") != ""


def ansi_color(color: int) -> str:
    return f"\x1b[{color}m"


class CommandFormatter(logging.Formatter):
    """
    print errors in red and warnings in yellow
    """

    def __init__(self) -> None:
        super().__init__(
            "%(prefix_color)s[%(command_prefix)s]%(color_reset)s %(color)s%(message)s%(color_reset)s"
        )
        self.hostnames: list[str] = []
        self.hostname_color_offset = 1  # first host shouldn't get aggressive red

    def format(self, record: logging.LogRecord) -> str:
        colorcode = 0
        if record.levelno == logging.ERROR:
            colorcode = 31  # red
        if record.levelno == logging.WARNING:
            colorcode = 33  # yellow

        color, prefix_color, color_reset = "", "", ""
        if not DISABLE_COLOR:
            command_prefix = getattr(record, "command_prefix", "")
            color = ansi_color(colorcode)
            prefix_color = ansi_color(self.hostname_colorcode(command_prefix))
            color_reset = "\x1b[0m"

        record.color = color
        record.prefix_color = prefix_color
        record.color_reset = color_reset

        return super().format(record)

    def hostname_colorcode(self, hostname: str) -> int:
        try:
            index = self.hostnames.index(hostname)
        except ValueError:
            self.hostnames += [hostname]
            index = self.hostnames.index(hostname)
        return 31 + (index + self.hostname_color_offset) % 7


def setup_loggers() -> tuple[logging.Logger, logging.Logger]:
    # If we use the default logger here (logging.error etc) or a logger called
    # "deploykit", then cmdlog messages are also posted on the default logger.
    # To avoid this message duplication, we set up a main and command logger
    # and use a "deploykit" main logger.
    kitlog = logging.getLogger("deploykit.main")
    kitlog.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter())

    kitlog.addHandler(ch)

    # use specific logger for command outputs
    cmdlog = logging.getLogger("deploykit.command")
    cmdlog.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(CommandFormatter())

    cmdlog.addHandler(ch)
    return (kitlog, cmdlog)


# loggers for: general deploykit, command output
kitlog, cmdlog = setup_loggers()

info = kitlog.info
warn = kitlog.warning
error = kitlog.error


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


FILE = None | int

# Seconds until a message is printed when _run produces no output.
NO_OUTPUT_TIMEOUT = 20


class HostKeyCheck(Enum):
    # Strictly check ssh host keys, prompt for unknown ones
    STRICT = 0
    # Ask for confirmation on first use
    ASK = 1
    # Trust on ssh keys on first use
    TOFU = 2
    # Do not check ssh host keys
    NONE = 3

    @staticmethod
    def from_str(label: str) -> "HostKeyCheck":
        if label.upper() in HostKeyCheck.__members__:
            return HostKeyCheck[label.upper()]
        msg = f"Invalid choice: {label}."
        description = "Choose from: " + ", ".join(HostKeyCheck.__members__)
        raise ClanError(msg, description=description)

    def __str__(self) -> str:
        return self.name.lower()

    def to_ssh_opt(self) -> list[str]:
        match self:
            case HostKeyCheck.STRICT:
                return ["-o", "StrictHostKeyChecking=yes"]
            case HostKeyCheck.ASK:
                return []
            case HostKeyCheck.TOFU:
                return ["-o", "StrictHostKeyChecking=accept-new"]
            case HostKeyCheck.NONE:
                return [
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                ]
            case _:
                msg = "Invalid HostKeyCheck"
                raise ClanError(msg)


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
        self.ssh_options = ssh_options

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
                        raise subprocess.CalledProcessError(
                            ret, cmd=cmd, output=stdout_data, stderr=stderr_data
                        )
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
        env["NIX_SSHOPTS"] = " ".join(self.ssh_cmd_opts())
        return env

    def ssh_cmd_opts(
        self,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> list[str]:
        ssh_opts = ["-A"] if self.forward_agent else []

        for k, v in self.ssh_options.items():
            ssh_opts.extend(["-o", f"{k}={shlex.quote(v)}"])

        if self.port:
            ssh_opts.extend(["-p", str(self.port)])
        if self.key:
            ssh_opts.extend(["-i", self.key])

        ssh_opts.extend(self.host_key_check.to_ssh_opt())
        if verbose_ssh or self.verbose_ssh:
            ssh_opts.extend(["-v"])
        if tty:
            ssh_opts.extend(["-t"])
        return ssh_opts

    def ssh_cmd(
        self,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> list[str]:
        return [
            "ssh",
            self.target,
            *self.ssh_cmd_opts(verbose_ssh=verbose_ssh, tty=tty),
        ]


T = TypeVar("T")


class HostResult(Generic[T]):
    def __init__(self, host: Host, result: T | Exception) -> None:
        self.host = host
        self._result = result

    @property
    def error(self) -> Exception | None:
        """
        Returns an error if the command failed
        """
        if isinstance(self._result, Exception):
            return self._result
        return None

    @property
    def result(self) -> T:
        """
        Unwrap the result
        """
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


Results = list[HostResult[subprocess.CompletedProcess[str]]]


def _worker(
    func: Callable[[Host], T],
    host: Host,
    results: list[HostResult[T]],
    idx: int,
) -> None:
    try:
        results[idx] = HostResult(host, func(host))
    except Exception as e:
        kitlog.exception(e)
        results[idx] = HostResult(host, e)


class HostGroup:
    def __init__(self, hosts: list[Host]) -> None:
        self.hosts = hosts

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"HostGroup({self.hosts})"

    def _run_local(
        self,
        cmd: str | list[str],
        host: Host,
        results: Results,
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        verbose_ssh: bool = False,
        timeout: float = math.inf,
        tty: bool = False,
    ) -> None:
        if extra_env is None:
            extra_env = {}
        try:
            proc = host.run_local(
                cmd,
                stdout=stdout,
                stderr=stderr,
                extra_env=extra_env,
                cwd=cwd,
                check=check,
                timeout=timeout,
            )
            results.append(HostResult(host, proc))
        except Exception as e:
            kitlog.exception(e)
            results.append(HostResult(host, e))

    def _run_remote(
        self,
        cmd: str | list[str],
        host: Host,
        results: Results,
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        verbose_ssh: bool = False,
        timeout: float = math.inf,
        tty: bool = False,
    ) -> None:
        if extra_env is None:
            extra_env = {}
        try:
            proc = host.run(
                cmd,
                stdout=stdout,
                stderr=stderr,
                extra_env=extra_env,
                cwd=cwd,
                check=check,
                verbose_ssh=verbose_ssh,
                timeout=timeout,
                tty=tty,
            )
            results.append(HostResult(host, proc))
        except Exception as e:
            kitlog.exception(e)
            results.append(HostResult(host, e))

    def _reraise_errors(self, results: list[HostResult[Any]]) -> None:
        errors = 0
        for result in results:
            e = result.error
            if e:
                cmdlog.error(
                    f"failed with: {e}",
                    extra={"command_prefix": result.host.command_prefix},
                )
                errors += 1
        if errors > 0:
            msg = f"{errors} hosts failed with an error. Check the logs above"
            raise ClanError(msg)

    def _run(
        self,
        cmd: str | list[str],
        local: bool = False,
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> Results:
        if extra_env is None:
            extra_env = {}
        results: Results = []
        threads = []
        for host in self.hosts:
            fn = self._run_local if local else self._run_remote
            thread = Thread(
                target=fn,
                kwargs={
                    "results": results,
                    "cmd": cmd,
                    "host": host,
                    "stdout": stdout,
                    "stderr": stderr,
                    "extra_env": extra_env,
                    "cwd": cwd,
                    "check": check,
                    "timeout": timeout,
                    "verbose_ssh": verbose_ssh,
                    "tty": tty,
                },
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        if check:
            self._reraise_errors(results)

        return results

    def run(
        self,
        cmd: str | list[str],
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        verbose_ssh: bool = False,
        timeout: float = math.inf,
        tty: bool = False,
    ) -> Results:
        """
        Command to run on the remote host via ssh
        @stdout if not None stdout of the command will be redirected to this file i.e. stdout=subprocss.PIPE
        @stderr if not None stderr of the command will be redirected to this file i.e. stderr=subprocess.PIPE
        @cwd current working directory to run the process in
        @verbose_ssh: Enables verbose logging on ssh connections
        @timeout: Timeout in seconds for the command to complete

        @return a lists of tuples containing Host and the result of the command for this Host
        """
        if extra_env is None:
            extra_env = {}
        return self._run(
            cmd,
            stdout=stdout,
            stderr=stderr,
            extra_env=extra_env,
            cwd=cwd,
            check=check,
            verbose_ssh=verbose_ssh,
            timeout=timeout,
            tty=tty,
        )

    def run_local(
        self,
        cmd: str | list[str],
        stdout: FILE = None,
        stderr: FILE = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
    ) -> Results:
        """
        Command to run locally for each host in the group in parallel
        @cmd the command to run
        @stdout if not None stdout of the command will be redirected to this file i.e. stdout=subprocss.PIPE
        @stderr if not None stderr of the command will be redirected to this file i.e. stderr=subprocess.PIPE
        @cwd current working directory to run the process in
        @extra_env environment variables to override when running the command
        @timeout: Timeout in seconds for the command to complete

        @return a lists of tuples containing Host and the result of the command for this Host
        """
        if extra_env is None:
            extra_env = {}
        return self._run(
            cmd,
            local=True,
            stdout=stdout,
            stderr=stderr,
            extra_env=extra_env,
            cwd=cwd,
            check=check,
            timeout=timeout,
        )

    def run_function(
        self, func: Callable[[Host], T], check: bool = True
    ) -> list[HostResult[T]]:
        """
        Function to run for each host in the group in parallel

        @func the function to call
        """
        threads = []
        results: list[HostResult[T]] = [
            HostResult(h, ClanError(f"No result set for thread {i}"))
            for (i, h) in enumerate(self.hosts)
        ]
        for i, host in enumerate(self.hosts):
            thread = Thread(
                target=_worker,
                args=(func, host, results, i),
            )
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        if check:
            self._reraise_errors(results)
        return results

    def filter(self, pred: Callable[[Host], bool]) -> "HostGroup":
        """Return a new Group with the results filtered by the predicate"""
        return HostGroup(list(filter(pred, self.hosts)))


def parse_deployment_address(
    machine_name: str,
    host: str,
    host_key_check: HostKeyCheck,
    forward_agent: bool = True,
    meta: dict[str, Any] | None = None,
) -> Host:
    if meta is None:
        meta = {}
    parts = host.split("@")
    user: str | None = None
    # count the number of : in the hostname
    if host.count(":") > 1 and not host.startswith("["):
        msg = f"Invalid hostname: {host}. IPv6 addresses must be enclosed in brackets , e.g. [::1]"
        raise ClanError(msg)
    if len(parts) > 1:
        user = parts[0]
        hostname = parts[1]
    else:
        hostname = parts[0]
    maybe_options = hostname.split("?")
    options: dict[str, str] = {}
    if len(maybe_options) > 1:
        hostname = maybe_options[0]
        for option in maybe_options[1].split("&"):
            k, v = option.split("=")
            options[k] = v
    result = urllib.parse.urlsplit("//" + hostname)
    if not result.hostname:
        msg = f"Invalid hostname: {hostname}"
        raise ClanError(msg)
    hostname = result.hostname
    port = result.port
    meta = meta.copy()
    return Host(
        hostname,
        user=user,
        port=port,
        host_key_check=host_key_check,
        command_prefix=machine_name,
        forward_agent=forward_agent,
        meta=meta,
        ssh_options=options,
    )
