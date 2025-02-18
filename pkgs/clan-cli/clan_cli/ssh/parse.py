import re
import urllib.parse
from typing import Any

from clan_cli.errors import ClanError
from clan_cli.ssh.host import Host
from clan_cli.ssh.host_key import HostKeyCheck


def parse_deployment_address(
    machine_name: str,
    host: str,
    host_key_check: HostKeyCheck,
    forward_agent: bool = True,
    meta: dict[str, Any] | None = None,
) -> Host:
    parts = host.split("?", maxsplit=1)
    endpoint, maybe_options = parts if len(parts) == 2 else (parts[0], "")

    parts = endpoint.split("@")
    match len(parts):
        case 2:
            user, host_port = parts
        case 1:
            user, host_port = "", parts[0]
        case _:
            msg = f"Invalid host, got `{host}` but expected something like `[user@]hostname[:port]`"
            raise ClanError(msg)

    # Make this check now rather than failing with a `ValueError`
    # when looking up the port from the `urlsplit` result below:
    if host_port.count(":") > 1 and not re.match(r".*\[.*]", host_port):
        msg = f"Invalid hostname: {host}. IPv6 addresses must be enclosed in brackets , e.g. [::1]"
        raise ClanError(msg)

    options: dict[str, str] = {}
    for o in maybe_options.split("&"):
        if len(o) == 0:
            continue
        parts = o.split("=", maxsplit=1)
        if len(parts) != 2:
            msg = (
                f"Invalid option in host `{host}`: option `{o}` does not have "
                f"a value (i.e. expected something like `name=value`)"
            )
            raise ClanError(msg)
        name, value = parts
        options[name] = value

    result = urllib.parse.urlsplit(f"//{host_port}")
    if not result.hostname:
        msg = f"Invalid host, got `{host}` but expected something like `[user@]hostname[:port]`"
        raise ClanError(msg)
    hostname = result.hostname
    port = result.port

    return Host(
        hostname,
        user=user,
        port=port,
        host_key_check=host_key_check,
        command_prefix=machine_name,
        forward_agent=forward_agent,
        meta={} if meta is None else meta.copy(),
        ssh_options=options,
    )
