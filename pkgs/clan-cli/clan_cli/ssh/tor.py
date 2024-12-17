#!/usr/bin/env python3

import argparse
import logging
import socket
import struct
import time
from dataclasses import dataclass

from clan_cli.async_run import AsyncRuntime
from clan_cli.cmd import Log, RunOpts, run
from clan_cli.errors import TorConnectionError, TorSocksError
from clan_cli.nix import nix_shell

log = logging.getLogger(__name__)


@dataclass
class TorTarget:
    onion: str
    port: int
    proxy_host: str = "127.0.0.1"
    proxy_port: int = 9050


def connect_to_tor_socks(sock: socket.socket, target: TorTarget) -> socket.socket:
    """
    Connects to a .onion host through Tor's SOCKS5 proxy using the standard library.

    Args:
        target (TorTarget): An object containing the .onion address, port, proxy host, and proxy port.

    Returns:
        socket.socket: A socket connected to the .onion address via Tor.
    """
    try:
        # 1. Create a socket to the Tor SOCKS proxy
        sock.connect((target.proxy_host, target.proxy_port))
    except ConnectionRefusedError as ex:
        msg = f"Failed to connect to Tor SOCKS proxy at {target.proxy_host}:{target.proxy_port}: {ex}"
        raise TorSocksError(msg) from ex

    # 2. SOCKS5 handshake
    sock.sendall(
        b"\x05\x01\x00"
    )  # SOCKS version (0x05), number of authentication methods (0x01), no-authentication (0x00)
    response = sock.recv(2)

    # Validate the SOCKS5 handshake response
    if response != b"\x05\x00":  # SOCKS version = 0x05, no-authentication = 0x00
        msg = f"SOCKS5 handshake failed, unexpected response: {response.hex()}"
        raise TorSocksError(msg)

    # 3. Connection request
    request = (
        b"\x05\x01\x00\x03"  # SOCKS version, connect command, reserved, address type = domainname
        + bytes([len(target.onion)])
        + target.onion.encode("utf-8")  # Add domain name length and domain name
        + struct.pack(">H", target.port)  # Add destination port in network byte order
    )
    sock.sendall(request)

    # Read the connection request response
    response = sock.recv(10)
    if response[1] != 0x00:  # 0x00 indicates success
        msg = f".onion address not reachable: {response[1]}"
        raise TorConnectionError(msg)

    return sock


def fetch_onion_content(target: TorTarget) -> str:
    """
    Fetches the HTTP response from a .onion service through a Tor SOCKS5 proxy.

    Args:
        target (TorTarget): An object containing the .onion address, port, proxy host, and proxy port.

    Returns:
        str: The HTTP response text, or an error message if something goes wrong.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Connect to the .onion service via the SOCKS proxy
        sock = connect_to_tor_socks(sock, target)

        # 1. Send an HTTP GET request
        request = f"GET / HTTP/1.1\r\nHost: {target.onion}\r\nConnection: close\r\n\r\n"
        sock.sendall(request.encode("utf-8"))

        # 2. Read the HTTP response
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        return response.decode("utf-8", errors="replace")


def is_tor_running() -> bool:
    """Checks if Tor is online."""
    try:
        tor_online_test()
    except TorSocksError:
        return False
    else:
        return True


def spawn_tor(runtime: AsyncRuntime) -> None:
    """
    Spawns a Tor process using `nix-shell` if Tor is not already running.
    """

    def start_tor() -> None:
        """Starts Tor process using nix-shell."""
        cmd_args = ["tor", "--HardwareAccel", "1"]
        packages = ["nixpkgs#tor"]
        cmd = nix_shell(packages, cmd_args)
        runtime.async_run(None, run, cmd, RunOpts(log=Log.BOTH))
        log.debug("Attempting to start Tor")

    # Check if Tor is already running
    if is_tor_running():
        log.info("Tor is running")
        return

    # Attempt to start Tor
    start_tor()

    # Continuously check if Tor has started
    while not is_tor_running():
        log.debug("Waiting for Tor to start...")
        time.sleep(0.2)
    log.info("Tor is now running")


def tor_online_test() -> bool:
    """
    Tests if Tor is online by attempting to fetch content from a known .onion service.
    Returns True if successful, False otherwise.
    """
    target = TorTarget(
        onion="duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion", port=80
    )
    try:
        response = fetch_onion_content(target)
    except TorConnectionError:
        return False
    else:
        return "duckduckgo" in response


def ssh_tor_reachable(target: TorTarget) -> bool:
    """
    Tests if SSH is reachable via Tor by attempting to connect to a known .onion service.
    Returns True if successful, False otherwise.
    """
    try:
        response = fetch_onion_content(target)
    except TorConnectionError:
        return False
    else:
        return "SSH-" in response


def main() -> None:
    """
    Main function to handle command-line arguments and execute the script.
    """
    parser = argparse.ArgumentParser(
        description="Interact with a .onion service through Tor SOCKS5 proxy."
    )
    parser.add_argument(
        "onion_url", type=str, help=".onion URL to connect to (e.g., 'example.onion')"
    )
    parser.add_argument(
        "--port", type=int, help="Port to connect to on the .onion URL (default: 80)"
    )
    parser.add_argument(
        "--proxy-host",
        type=str,
        default="127.0.0.1",
        help="Address of the Tor SOCKS5 proxy (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--proxy-port",
        type=int,
        default=9050,
        help="Port of the Tor SOCKS5 proxy (default: 9050)",
    )
    parser.add_argument(
        "--ssh-tor-reachable",
        action="store_true",
        help="Test if SSH is reachable via Tor",
    )

    args = parser.parse_args()
    default_port = 22 if args.ssh_tor_reachable else 80

    # Create a TorTarget instance
    target = TorTarget(
        onion=args.onion_url,
        port=args.port or default_port,
        proxy_host=args.proxy_host,
        proxy_port=args.proxy_port,
    )

    if args.ssh_tor_reachable:
        print(f"Testing if SSH is reachable via Tor for {target.onion}...")
        reachable = ssh_tor_reachable(target)
        print(f"SSH is {'reachable' if reachable else 'not reachable'} via Tor.")
        return

    print(
        f"Connecting to {target.onion} on port {target.port} via proxy {target.proxy_host}:{target.proxy_port}..."
    )
    try:
        response = fetch_onion_content(target)
        print("Response:")
        print(response)
    except TorSocksError:
        log.error("Failed to connect to the Tor SOCKS proxy.")
        log.error(
            "Is Tor running? If not, you can start it by running 'tor' in a nix-shell."
        )
    except TorConnectionError:
        log.error("The onion address is not reachable via Tor.")


if __name__ == "__main__":
    main()
