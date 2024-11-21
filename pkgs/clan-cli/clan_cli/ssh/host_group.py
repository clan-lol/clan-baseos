import math
from collections.abc import Callable
from pathlib import Path
from threading import Thread
from typing import Any

from clan_cli.errors import ClanError
from clan_cli.ssh import T
from clan_cli.ssh.host import FILE, Host
from clan_cli.ssh.logger import cmdlog
from clan_cli.ssh.results import HostResult, Results


def _worker(
    func: Callable[[Host], T],
    host: Host,
    results: list[HostResult[T]],
    idx: int,
) -> None:
    try:
        results[idx] = HostResult(host, func(host))
    except Exception as e:
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
        if cwd is not None:
            msg = "cwd is not supported for remote commands"
            raise ClanError(msg)
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
