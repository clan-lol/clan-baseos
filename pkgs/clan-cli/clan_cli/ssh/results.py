import subprocess
from typing import Generic

from clan_cli.ssh import T
from clan_cli.ssh.host import Host


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
