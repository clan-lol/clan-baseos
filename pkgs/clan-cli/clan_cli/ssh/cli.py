import argparse
import json
import logging
import socket
import subprocess

from ..nix import nix_shell

log = logging.getLogger(__name__)


def ssh(
    host: str,
    user: str = "root",
    password: str | None = None,
    ssh_args: list[str] = [],
    torify: bool = False,
) -> None:
    packages = ["nixpkgs#openssh"]
    if torify:
        packages.append("nixpkgs#tor")

    password_args = []
    if password:
        packages.append("nixpkgs#sshpass")
        password_args = [
            "sshpass",
            "-p",
            password,
        ]
    _ssh_args = [
        *ssh_args,
        "ssh",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "StrictHostKeyChecking=no",
        f"{user}@{host}",
    ]

    cmd_args = [*password_args, *_ssh_args]
    if torify:
        cmd_args.insert(0, "torify")

    cmd = nix_shell(packages, cmd_args)
    subprocess.run(cmd)


def qrcode_scan(picture_file: str) -> str:
    return (
        subprocess.run(
            nix_shell(
                ["nixpkgs#zbar"],
                [
                    "zbarimg",
                    "--quiet",
                    "--raw",
                    picture_file,
                ],
            ),
            stdout=subprocess.PIPE,
            check=True,
        )
        .stdout.decode()
        .strip()
    )


def is_reachable(host: str) -> bool:
    sock = socket.socket(
        socket.AF_INET6 if ":" in host else socket.AF_INET, socket.SOCK_STREAM
    )
    sock.settimeout(2)
    try:
        sock.connect((host, 22))
        sock.close()
        return True
    except OSError:
        return False


def connect_ssh_from_json(ssh_data: dict[str, str]) -> None:
    for address in ssh_data["addrs"]:
        log.debug(f"Trying to reach host on: {address}")
        if is_reachable(address):
            ssh(host=address, password=ssh_data["pass"])
            exit(0)
        else:
            log.debug(f"Could not reach host on {address}")
    log.debug(f'Trying to reach host via torify on {ssh_data["tor"]}')
    ssh(host=ssh_data["tor"], password=ssh_data["pass"], torify=True)


def main(args: argparse.Namespace) -> None:
    if args.json:
        with open(args.json) as file:
            ssh_data = json.load(file)
        connect_ssh_from_json(ssh_data)
    elif args.png:
        ssh_data = json.loads(qrcode_scan(args.png))
        connect_ssh_from_json(ssh_data)


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
    # TODO pass all args we don't parse into ssh_args, currently it fails if arg starts with -
    parser.add_argument("ssh_args", nargs="*", default=[])
    parser.set_defaults(func=main)
