import base64
import http.client
import json


def get_context() -> http.client.ssl.SSLContext:
    # context = http.client.ssl.create_default_context()
    # # context.load_cert_chain(
    # #     certfile="/var/lib/sunshine/sunshine.cert", keyfile="/var/lib/sunshine/sunshine.key"
    # # )
    # context.load_cert_chain(
    #     certfile="/home/kenji/.config/sunshine/credentials/cacert.pem",
    #     keyfile="/home/kenji/.config/sunshine/credentials/cakey.pem",
    # )
    return http.client.ssl._create_unverified_context()  # noqa: SLF001


def pair(pin: str) -> str:
    conn = http.client.HTTPSConnection("localhost", 47990, context=get_context())

    # TODO: dynamic username and password
    user_and_pass = base64.b64encode(b"sunshine:sunshine").decode("ascii")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {user_and_pass}",
    }

    # Define the parameters
    params = json.dumps({"pin": f"{pin}"})

    # Make the request
    conn.request("POST", "/api/pin", params, headers)

    # Get and print the response
    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))
    return data.decode("utf-8")


def restart() -> None:
    # Define the connection
    conn = http.client.HTTPSConnection(
        "localhost",
        47990,
        context=http.client.ssl._create_unverified_context(),  # noqa: SLF001
    )
    user_and_pass = base64.b64encode(b"sunshine:sunshine").decode("ascii")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {user_and_pass}",
    }

    # Define the parameters
    params = {}

    # Make the request
    conn.request("POST", "/api/restart", params, headers)

    # Get and print the response
    # There wont be a response, because it is restarted
    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))
