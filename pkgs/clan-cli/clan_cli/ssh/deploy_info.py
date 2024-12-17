import argparse
import ipaddress
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clan_cli.async_run import AsyncRuntime
from clan_cli.cmd import run
from clan_cli.errors import ClanError
from clan_cli.nix import nix_shell
from clan_cli.ssh.host import Host, is_ssh_reachable
from clan_cli.ssh.tor import TorTarget, spawn_tor, ssh_tor_reachable

log = logging.getLogger(__name__)


@dataclass
class DeployInfo:
    addrs: list[str]
    tor: str | None = None
    pwd: str | None = None

    @staticmethod
    def from_json(data: dict[str, Any]) -> "DeployInfo":
        return DeployInfo(tor=data["tor"], pwd=data["pass"], addrs=data["addrs"])


def is_ipv6(ip: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(ip), ipaddress.IPv6Address)
    except ValueError:
        return False


def find_reachable_host(deploy_info: DeployInfo) -> Host | None:
    host = None
    for addr in deploy_info.addrs:
        host_addr = f"[{addr}]" if is_ipv6(addr) else addr
        host = Host(host=host_addr)
        if is_ssh_reachable(host):
            break
    return host


def qrcode_scan(picture_file: Path) -> str:
    cmd = nix_shell(
        ["nixpkgs#zbar"],
        [
            "zbarimg",
            "--quiet",
            "--raw",
            str(picture_file),
        ],
    )
    res = run(cmd)
    return res.stdout.strip()


def parse_qr_code(picture_file: Path) -> DeployInfo:
    data = qrcode_scan(picture_file)
    return DeployInfo.from_json(json.loads(data))


def ssh_shell_from_deploy(deploy_info: DeployInfo, runtime: AsyncRuntime) -> None:
    if host := find_reachable_host(deploy_info):
        host.connect_ssh_shell(password=deploy_info.pwd)
    else:
        log.info("Could not reach host via clearnet 'addrs'")
        log.info(f"Trying to reach host via tor '{deploy_info.tor}'")
        spawn_tor(runtime)
        if not deploy_info.tor:
            msg = "No tor address provided, please provide a tor address."
            raise ClanError(msg)
        if ssh_tor_reachable(TorTarget(onion=deploy_info.tor, port=22)):
            host = Host(host=deploy_info.tor)
            host.connect_ssh_shell(password=deploy_info.pwd, tor_socks=True)
        else:
            msg = "Could not reach host via tor either."
            raise ClanError(msg)


def ssh_command_parse(args: argparse.Namespace) -> DeployInfo | None:
    if args.json:
        json_file = Path(args.json)
        if json_file.is_file():
            data = json.loads(json_file.read_text())
            return DeployInfo.from_json(data)
        data = json.loads(args.json)
        return DeployInfo.from_json(data)
    if args.png:
        return parse_qr_code(Path(args.png))
    return None


def ssh_command(args: argparse.Namespace) -> None:
    deploy_info = ssh_command_parse(args)
    if not deploy_info:
        msg = "No --json or --png data provided"
        raise ClanError(msg)

    with AsyncRuntime() as runtime:
        ssh_shell_from_deploy(deploy_info, runtime)


def register_parser(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-j",
        "--json",
        help="specify the json file for ssh data (generated by starting the clan installer)",
    )
    group.add_argument(
        "-P",
        "--png",
        help="specify the json file for ssh data as the qrcode image (generated by starting the clan installer)",
    )
    parser.add_argument(
        "--ssh_args", nargs=argparse.REMAINDER, help="additional ssh arguments"
    )
    parser.set_defaults(func=ssh_command)
