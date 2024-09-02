import argparse
import base64
import json
import socket
import traceback

from .api import pair
from .state import default_sunshine_state_file


# listen on a specific port for information from the moonlight side
def listen(port: int, cert: str, uuid: str, state_file: str) -> bool:
    host = ""
    # Create a socket object with dual-stack support
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    # Enable dual-stack support
    server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    # Bind the socket to the host and port
    server_socket.bind((host, port))
    # Listen for incoming connections (accept up to 5)
    server_socket.listen(5)

    while True:
        # Accept incoming connection
        client_socket, addr = server_socket.accept()

        print(f"Connection accepted from {addr}")

        # Receive data from the client

        data = client_socket.recv(16384)

        try:
            request = data.decode("utf-8")
            raw_body = request.split("\n")[-1]
            print(raw_body)
            body = json.loads(raw_body)

            pair_type = body.get("type", "")

            if pair_type == "api":
                print("Api request")
                status = pair(body.get("pin", ""))
                status = json.dumps(status)
                response = f"HTTP/1.1 200 OK\r\nContent-Type:application/json\r\n\r\\{status}\r\n"
                client_socket.sendall(response.encode("utf-8"))

            if pair_type == "native":
                # url = unquote(data_str.split()[1])
                # rec_uuid = parse_qs(urlparse(url).query).get("uuid", [""])[0]
                # rec_cert = parse_qs(urlparse(url).query).get("cert", [""])[0]
                # decoded_cert = base64.urlsafe_b64decode(rec_cert).decode("utf-8")
                # print(f"Received URL: {url}")
                # print(f"Extracted UUID: {rec_uuid}")
                # print(f"Extracted Cert: {decoded_cert}")
                encoded_cert = base64.urlsafe_b64encode(cert.encode("utf-8")).decode(
                    "utf-8"
                )
                json_data = {}
                json_data["uuid"] = uuid
                json_data["cert"] = encoded_cert
                json_data["hostname"] = socket.gethostname()
                json_body = json.dumps(json_data)
                response = f"HTTP/1.1 200 OK\r\nContent-Type:application/json\r\n\r\\{json_body}\r\n"
                client_socket.sendall(response.encode("utf-8"))
                # add_moonlight_client(decoded_cert, state_file, rec_uuid)

        except UnicodeDecodeError:
            print(f"UnicodeDecodeError: Cannot decode byte {data[8]}")
            traceback.print_exc()

        client_socket.close()


def init_listener(args: argparse.Namespace) -> None:
    port = args.port
    cert = args.cert
    uuid = args.uuid
    state = args.state
    listen(port, cert, uuid, state)


def register_socket_listener(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", default=48011, type=int)
    parser.add_argument("--cert")
    parser.add_argument("--uuid")
    parser.add_argument("--state", default=default_sunshine_state_file())
    # TODO: auto accept
    # parser.add_argument("--auto-accept")
    parser.set_defaults(func=init_listener)
