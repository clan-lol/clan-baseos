import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Thread
from typing import IO, Any

from clan_cli.cmd import Log
from clan_cli.errors import ClanError
from clan_cli.ssh import T
from clan_cli.ssh.host import Host
from clan_cli.ssh.results import HostResult, Results

cmdlog = logging.getLogger(__name__)


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


@dataclass
class HostGroup:
    hosts: list[Host]

    def _run_local(
        self,
        cmd: list[str],
        host: Host,
        results: Results,
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | Path = None,
        check: bool = True,
        verbose_ssh: bool = False,
        timeout: float = math.inf,
        shell: bool = False,
        tty: bool = False,
        log: Log = Log.BOTH,
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
                shell=shell,
                log=log,
            )
            results.append(HostResult(host, proc))
        except Exception as e:
            results.append(HostResult(host, e))

    def _run_remote(
        self,
        cmd: list[str],
        host: Host,
        results: Results,
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        verbose_ssh: bool = False,
        timeout: float = math.inf,
        tty: bool = False,
        shell: bool = False,
        log: Log = Log.BOTH,
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
                shell=shell,
                log=log,
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
        cmd: list[str],
        local: bool = False,
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        verbose_ssh: bool = False,
        tty: bool = False,
        shell: bool = False,
        log: Log = Log.BOTH,
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
                    "shell": shell,
                    "log": log,
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
        cmd: list[str],
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        verbose_ssh: bool = False,
        timeout: float = math.inf,
        tty: bool = False,
        log: Log = Log.BOTH,
        shell: bool = False,
    ) -> Results:
        """
        Command to run on the remote host via ssh

        @return a lists of tuples containing Host and the result of the command for this Host
        """
        if extra_env is None:
            extra_env = {}
        return self._run(
            cmd,
            shell=shell,
            stdout=stdout,
            stderr=stderr,
            extra_env=extra_env,
            cwd=cwd,
            check=check,
            verbose_ssh=verbose_ssh,
            timeout=timeout,
            tty=tty,
            log=log,
        )

    def run_local(
        self,
        cmd: list[str],
        stdout: IO[bytes] | None = None,
        stderr: IO[bytes] | None = None,
        extra_env: dict[str, str] | None = None,
        cwd: None | str | Path = None,
        check: bool = True,
        timeout: float = math.inf,
        shell: bool = False,
        log: Log = Log.BOTH,
    ) -> Results:
        """
        Command to run locally for each host in the group in parallel

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
            shell=shell,
            log=log,
        )

    def run_function(
        self, func: Callable[[Host], T], check: bool = True
    ) -> list[HostResult[T]]:
        """
        Function to run for each host in the group in parallel
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
