import argparse
import re
from dataclasses import dataclass

from clan_cli.cmd import run_no_stdout
from clan_cli.nix import nix_shell

from . import API


@dataclass
class Host:
    # Part of the discovery
    interface: str
    protocol: str
    name: str
    type_: str
    domain: str
    # Optional, only if more data is available
    host: str | None
    ip: str | None
    port: str | None
    txt: str | None


@dataclass
class DNSInfo:
    """ "
    mDNS/DNS-SD services discovered on the network
    """

    services: dict[str, Host]


def decode_escapes(s: str) -> str:
    return re.sub(r"\\(\d{3})", lambda x: chr(int(x.group(1))), s)


def parse_avahi_output(output: str) -> DNSInfo:
    dns_info = DNSInfo(services={})
    for line in output.splitlines():
        parts = line.split(";")
        # New service discovered
        # print(parts)
        if parts[0] == "+" and len(parts) >= 6:
            interface, protocol, name, type_, domain = parts[1:6]

            name = decode_escapes(name)

            dns_info.services[name] = Host(
                interface=interface,
                protocol=protocol,
                name=name,
                type_=decode_escapes(type_),
                domain=domain,
                host=None,
                ip=None,
                port=None,
                txt=None,
            )

        # Resolved more data for already discovered services
        elif parts[0] == "=" and len(parts) >= 9:
            interface, protocol, name, type_, domain, host, ip, port = parts[1:9]

            name = decode_escapes(name)

            if name in dns_info.services:
                dns_info.services[name].host = decode_escapes(host)
                dns_info.services[name].ip = ip
                dns_info.services[name].port = port
                if len(parts) > 9:
                    dns_info.services[name].txt = decode_escapes(parts[9])
            else:
                dns_info.services[name] = Host(
                    interface=parts[1],
                    protocol=parts[2],
                    name=name,
                    type_=decode_escapes(parts[4]),
                    domain=parts[5],
                    host=decode_escapes(parts[6]),
                    ip=parts[7],
                    port=parts[8],
                    txt=decode_escapes(parts[9]) if len(parts) > 9 else None,
                )

    return dns_info


@API.register
def show_mdns() -> DNSInfo:
    cmd = nix_shell(
        ["nixpkgs#avahi"],
        [
            "avahi-browse",
            "--all",
            "--resolve",
            "--parsable",
            "-l",  # Ignore local services
            "--terminate",
        ],
    )
    proc = run_no_stdout(cmd)
    data = parse_avahi_output(proc.stdout)

    return data


def mdns_command(args: argparse.Namespace) -> None:
    dns_info = show_mdns()
    for name, info in dns_info.services.items():
        print(f"Hostname: {name} - ip: {info.ip}")


def register_mdns(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=mdns_command)
