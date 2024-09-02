import argparse
import base64
import json
import socket

from .run import MoonlightPairing
from .state import add_sunshine_host, gen_pin, get_moonlight_certificate
from .uri import parse_moonlight_uri


def send_join_request(host: str, port: int, cert: str) -> bool:
    max_tries = 3
    response = False
    for _tries in range(max_tries):
        response = send_join_request_api(host, port)
        if response:
            return response
    return bool(send_join_request_native(host, port, cert))


# This is the preferred join method, but sunshines pin mechanism
# seems to be somewhat brittle in repeated testing, retry then fallback to native
def send_join_request_api(host: str, port: int) -> bool:
    moonlight = MoonlightPairing()
    # is_paired = moonlight.check(host)
    is_paired = False
    if is_paired:
        print(f"Moonlight is already paired with this host: {host}")
        return True
    pin = gen_pin()
    moonlight.init_pairing(host, pin)
    moonlight.wait_until_started()

    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        json_body = json.dumps({"type": "api", "pin": pin})
        request = (
            f"POST / HTTP/1.1\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(json_body)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{json_body}"
        )
        try:
            s.sendall(request.encode("utf-8"))
            response = s.recv(16384).decode("utf-8")
            print(response)
            body = response.split("\n")[-1]
            print(body)
            moonlight.terminate()
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            moonlight.terminate()
            return False


def send_join_request_native(host: str, port: int, cert: str) -> bool:
    # This is the hardcoded UUID for the moonlight client
    uuid = "123456789ABCD"
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        encoded_cert = base64.urlsafe_b64encode(cert.encode("utf-8")).decode("utf-8")
        json_body_str = json.dumps(
            {"type": "native", "uuid": uuid, "cert": encoded_cert}
        )
        request = (
            f"POST / HTTP/1.1\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(json_body_str)}\r\n"
            f"Connection: close\r\n\r\n"
            f"{json_body_str}"
        )
        try:
            s.sendall(request.encode("utf-8"))
            response = s.recv(16384).decode("utf-8")
            print(response)
            lines = response.split("\n")
            body = "\n".join(lines[2:])[2:]
            print(body)
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
    # TODO: fix
    try:
        print(f"response: {response}")
        data = json.loads(response)
        print(f"Data: {data}")
        print(f"Host uuid: {data['uuid']}")
        print(f"Host certificate: {data['cert']}")
        print("Joining sunshine host")
        cert = data["cert"]
        cert = base64.urlsafe_b64decode(cert).decode("utf-8")
        uuid = data["uuid"]
        hostname = data["hostname"]
        add_sunshine_host(hostname, host, cert, uuid)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        pos = e.pos
        print(f"Failed to decode JSON: unexpected character {response[pos]}")
    return False


def join(args: argparse.Namespace) -> None:
    if args.url:
        (host, port) = parse_moonlight_uri(args.url)
        if port is None:
            port = 48011
    else:
        port = args.port
        host = args.host

    print(f"Host: {host}, port: {port}")
    # TODO: If cert is not provided parse from config
    # cert = args.cert
    cert = get_moonlight_certificate()
    assert port is not None
    if send_join_request(host, port, cert):
        print(f"Successfully joined sunshine host: {host}")
    else:
        print(f"Failed to join sunshine host: {host}")


def register_join_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url", nargs="?")
    parser.add_argument("--port", type=int, default=48011)
    parser.add_argument("--host")
    parser.add_argument("--cert")
    parser.set_defaults(func=join)
