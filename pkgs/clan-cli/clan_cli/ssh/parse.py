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
    if meta is None:
        meta = {}
    parts = host.split("@")
    user: str | None = None
    # count the number of : in the hostname
    if host.count(":") > 1 and not re.match(r".*\[.*\]", host):
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
