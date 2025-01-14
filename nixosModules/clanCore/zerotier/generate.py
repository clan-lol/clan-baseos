import argparse
import contextlib
import ipaddress
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


class ClanError(Exception):
    pass


def try_bind_port(port: int) -> bool:
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with tcp, udp:
        try:
            tcp.bind(("127.0.0.1", port))
            udp.bind(("127.0.0.1", port))
        except OSError:
            return False
        else:
            return True


def try_connect_port(port: int) -> bool:
    sock = socket.socket(socket.AF_INET)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    return result == 0


def find_free_port() -> int | None:
    """Find an unused localhost port from 1024-65535 and return it."""
    with contextlib.closing(socket.socket(type=socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Identity:
    def __init__(self, path: Path) -> None:
        self.public = (path / "identity.public").read_text()
        self.private = (path / "identity.secret").read_text()

    def node_id(self) -> str:
        nid = self.public.split(":")[0]
        assert len(nid) == 10, (
            f"node_id must be 10 characters long, got {len(nid)}: {nid}"
        )
        return nid


class ZerotierController:
    def __init__(self, port: int, home: Path) -> None:
        self.port = port
        self.home = home
        self.authtoken = (home / "authtoken.secret").read_text()
        self.identity = Identity(home)

    def _http_request(
        self,
        path: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if headers is None:
            headers = {}
        body = None
        headers = headers.copy()
        if data is not None:
            body = json.dumps(data).encode("ascii")
            headers["Content-Type"] = "application/json"
        headers["X-ZT1-AUTH"] = self.authtoken
        url = f"http://127.0.0.1:{self.port}{path}"
        req = urllib.request.Request(url, headers=headers, method=method, data=body)
        resp = urllib.request.urlopen(req)
        return json.load(resp)

    def status(self) -> dict[str, Any]:
        return self._http_request("/status")

    def create_network(self, data: dict[str, Any] | None = None) -> dict[str, Any]:
        if data is None:
            data = {}
        return self._http_request(
            f"/controller/network/{self.identity.node_id()}______",
            method="POST",
            data=data,
        )

    def get_network(self, network_id: str) -> dict[str, Any]:
        return self._http_request(f"/controller/network/{network_id}")


@contextmanager
def zerotier_controller() -> Iterator[ZerotierController]:
    # This check could be racy but it's unlikely in practice
    controller_port = find_free_port()
    if controller_port is None:
        msg = "cannot find a free port for zerotier controller"
        raise ClanError(msg)

    with TemporaryDirectory() as d:
        tempdir = Path(d)
        home = tempdir / "zerotier-one"
        home.mkdir()
        cmd = [
            "zerotier-one",
            f"-p{controller_port}",
            str(home),
        ]

        with subprocess.Popen(cmd, start_new_session=True) as p:
            process_group = os.getpgid(p.pid)
            try:
                print(
                    f"wait for controller to be started on 127.0.0.1:{controller_port}...",
                )
                while not try_connect_port(controller_port):
                    status = p.poll()
                    if status is not None:
                        msg = (
                            f"zerotier-one has been terminated unexpected with {status}"
                        )
                        raise ClanError(msg)
                    time.sleep(0.1)
                print()

                yield ZerotierController(controller_port, home)
            finally:
                os.killpg(process_group, signal.SIGKILL)


@dataclass
class NetworkController:
    networkid: str
    identity: Identity


# TODO: allow merging more network configuration here
def create_network_controller() -> NetworkController:
    e = ClanError("Bug, should never happen")
    for _ in range(10):
        try:
            with zerotier_controller() as controller:
                network = controller.create_network()
                return NetworkController(network["nwid"], controller.identity)
        except ClanError:  # probably failed to allocate port, so retry
            print("failed to create network, retrying..., probabl", file=sys.stderr)
    raise e


def create_identity() -> Identity:
    with TemporaryDirectory() as d:
        tmpdir = Path(d)
        private = tmpdir / "identity.secret"
        public = tmpdir / "identity.public"
        subprocess.run(["zerotier-idtool", "generate", private, public], check=True)
        return Identity(tmpdir)


def compute_zerotier_ip(network_id: str, identity: Identity) -> ipaddress.IPv6Address:
    assert len(network_id) == 16, (
        f"network_id must be 16 characters long, got '{network_id}'"
    )
    nwid = int(network_id, 16)
    node_id = int(identity.node_id(), 16)
    addr_parts = bytearray(
        [
            0xFD,
            (nwid >> 56) & 0xFF,
            (nwid >> 48) & 0xFF,
            (nwid >> 40) & 0xFF,
            (nwid >> 32) & 0xFF,
            (nwid >> 24) & 0xFF,
            (nwid >> 16) & 0xFF,
            (nwid >> 8) & 0xFF,
            (nwid) & 0xFF,
            0x99,
            0x93,
            (node_id >> 32) & 0xFF,
            (node_id >> 24) & 0xFF,
            (node_id >> 16) & 0xFF,
            (node_id >> 8) & 0xFF,
            (node_id) & 0xFF,
        ]
    )
    return ipaddress.IPv6Address(bytes(addr_parts))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=["network", "identity"], required=True, type=str
    )
    parser.add_argument("--ip", type=Path, required=True)
    parser.add_argument("--identity-secret", type=Path, required=True)
    parser.add_argument("--network-id", type=str, required=False)
    args = parser.parse_args()

    match args.mode:
        case "network":
            if args.network_id is None:
                msg = "network_id parameter is required"
                raise ClanError(msg)
            controller = create_network_controller()
            identity = controller.identity
            network_id = controller.networkid
            Path(args.network_id).write_text(network_id)
        case "identity":
            identity = create_identity()
            network_id = args.network_id
        case _:
            msg = f"unknown mode {args.mode}"
            raise ClanError(msg)
    ip = compute_zerotier_ip(network_id, identity)

    args.identity_secret.write_text(identity.private)
    args.ip.write_text(ip.compressed)


if __name__ == "__main__":
    main()
