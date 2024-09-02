from urllib.parse import urlparse


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
        raise ValueError(msg)
    hostname = parsed.hostname
    if hostname is None:
        msg = f"Invalid moonlight URI: {uri}"
        raise ValueError
    port = parsed.port
    return (hostname, port)
