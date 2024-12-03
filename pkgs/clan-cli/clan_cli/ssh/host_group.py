import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import Thread
from typing import Any

from clan_cli.cmd import RunOpts
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
        *,
        cmd: list[str],
        opts: RunOpts,
        extra_env: dict[str, str] | None,
        host: Host,
        results: Results,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> None:
        try:
            proc = host.run_local(
                cmd,
                opts,
                extra_env,
            )
            results.append(HostResult(host, proc))
        except Exception as e:
            results.append(HostResult(host, e))

    def _run_remote(
        self,
        cmd: list[str],
        opts: RunOpts,
        host: Host,
        results: Results,
        extra_env: dict[str, str] | None = None,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> None:
        try:
            proc = host.run(
                cmd,
                extra_env=extra_env,
                verbose_ssh=verbose_ssh,
                opts=opts,
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
            raise ClanError(msg) from e

    def _run(
        self,
        cmd: list[str],
        opts: RunOpts | None = None,
        local: bool = False,
        extra_env: dict[str, str] | None = None,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> Results:
        results: Results = []
        threads = []

        if opts is None:
            opts = RunOpts()

        for host in self.hosts:
            if local:
                thread = Thread(
                    target=self._run_local,
                    kwargs={
                        "cmd": cmd,
                        "opts": opts,
                        "host": host,
                        "results": results,
                        "extra_env": extra_env,
                        "verbose_ssh": verbose_ssh,
                        "tty": tty,
                    },
                )
            else:
                thread = Thread(
                    target=self._run_remote,
                    kwargs={
                        "results": results,
                        "cmd": cmd,
                        "host": host,
                        "opts": opts,
                        "extra_env": extra_env,
                        "verbose_ssh": verbose_ssh,
                        "tty": tty,
                    },
                )

            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        if opts.check:
            self._reraise_errors(results)

        return results

    def run(
        self,
        cmd: list[str],
        opts: RunOpts | None = None,
        *,
        extra_env: dict[str, str] | None = None,
        verbose_ssh: bool = False,
        tty: bool = False,
    ) -> Results:
        """
        Command to run on the remote host via ssh

        @return a lists of tuples containing Host and the result of the command for this Host
        """
        return self._run(
            cmd,
            opts,
            extra_env=extra_env,
            verbose_ssh=verbose_ssh,
            tty=tty,
        )

    def run_local(
        self,
        cmd: list[str],
        opts: RunOpts | None = None,
        *,
        extra_env: dict[str, str] | None = None,
    ) -> Results:
        """
        Command to run locally for each host in the group in parallel

        @return a lists of tuples containing Host and the result of the command for this Host
        """

        return self._run(
            cmd,
            opts,
            local=True,
            extra_env=extra_env,
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
