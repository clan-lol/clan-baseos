from urllib.parse import urlparse

from moonlight_sunshine_accept.errors import Error


def parse_moonlight_uri(uri: str) -> tuple[str, int | None]:
    print(uri)
    if uri.startswith("moonlight:"):
        # Fixes a bug where moonlight:// is not parsed correctly
        uri = uri[10:]
        uri = "moonlight://" + uri
    print(uri)
    parsed = urlparse(uri)
    if parsed.scheme != "moonlight":
        msg = f"Invalid moonlight URI: {uri}"
        raise Error(msg)
    hostname = parsed.hostname
    if hostname is None:
        msg = f"Invalid moonlight URI: {uri}"
        raise Error(msg)
    port = parsed.port
    return (hostname, port)
