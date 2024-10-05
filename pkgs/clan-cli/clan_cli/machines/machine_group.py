from collections.abc import Callable
from typing import TypeVar

from clan_cli.ssh import Host, HostGroup, HostResult

from .machines import Machine

T = TypeVar("T")


class MachineGroup:
    def __init__(self, machines: list[Machine]) -> None:
        self.group = HostGroup([m.target_host for m in machines])

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"MachineGroup({self.group})"

    def run_function(
        self, func: Callable[[Machine], T], check: bool = True
    ) -> list[HostResult[T]]:
        """
        Function to run for each host in the group in parallel

        @func the function to call
        """

        def wrapped_func(host: Host) -> T:
            return func(host.meta["machine"])

        return self.group.run_function(wrapped_func, check=check)
