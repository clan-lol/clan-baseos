# Import the urllib.parse, enum and dataclasses modules
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from clan_cli.flake import Flake


# Define the ClanURI class
@dataclass
class ClanURI:
    flake: Flake
    machine_name: str

    def get_url(self) -> str:
        return str(self.flake)

    @classmethod
    def from_str(
        cls,
        url: str,
        machine_name: str | None = None,
    ) -> "ClanURI":
        uri = url

        if machine_name:
            uri += f"#{machine_name}"

        # Users might copy whitespace along with the URI
        uri = uri.strip()

        # Check if the URI starts with clan://
        # If it does, remove the clan:// prefix
        prefix = "clan://"
        if uri.startswith(prefix):
            uri = uri[len(prefix) :]

        # Fix missing colon (caused by browsers like Firefox)
        if "//" in uri and ":" not in uri.split("//", 1)[0]:
            # If there's a `//` but no colon before it, add one before the `//`
            parts = uri.split("//", 1)
            uri = f"{parts[0]}://{parts[1]}"

        # Parse the URI into components
        # url://netloc/path;parameters?query#fragment
        components: urllib.parse.ParseResult = urllib.parse.urlparse(uri)

        # Replace the query string in the components with the new query string
        clean_comps = components._replace(query=components.query, fragment="")

        # Parse the URL into a ClanUrl object
        if clean_comps.path and Path(clean_comps.path).exists():
            flake = Flake(clean_comps.path)
        else:
            flake = Flake(clean_comps.geturl())
        machine_name = "defaultVM"
        if components.fragment:
            machine_name = components.fragment

        return cls(flake, machine_name)
