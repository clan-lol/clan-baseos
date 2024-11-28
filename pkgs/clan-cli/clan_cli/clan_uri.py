# Import the urllib.parse, enum and dataclasses modules
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FlakeId:
    loc: str

    @classmethod
    def from_json(cls: type["FlakeId"], data: dict[str, Any]) -> "FlakeId":
        return cls(loc=data["loc"])

    def __str__(self) -> str:
        return str(self.loc)

    def __hash__(self) -> int:
        return hash(str(self.loc))

    @property
    def path(self) -> Path:
        assert self.is_local(), f"Flake {self.loc} is not a local path"
        return Path(self.loc)

    @property
    def url(self) -> str:
        assert self.is_remote(), f"Flake {self.loc} is not a remote url"
        return str(self.loc)

    def is_local(self) -> bool:
        """
        https://nix.dev/manual/nix/2.22/language/builtins.html?highlight=urlS#source-types

        Examples:

        - file:///home/eelco/nix/README.md          file        LOCAL
        - git+file://git:github.com:NixOS/nixpkgs   git+file    LOCAL
        - https://example.com/index.html            https       REMOTE
        - github:nixos/nixpkgs                      github      REMOTE
        - ftp://serv.file                           ftp         REMOTE
        - ./.                                       ''          LOCAL

        """
        x = urllib.parse.urlparse(str(self.loc))
        # See above *file* or empty are the only local schemas
        return x.scheme == "" or "file" in x.scheme

    def is_remote(self) -> bool:
        return not self.is_local()


def _parse_url(comps: urllib.parse.ParseResult) -> FlakeId:
    if comps.scheme == "" or "file" in comps.scheme:
        res_p = Path(comps.path).expanduser().resolve()
        flake_id = FlakeId(str(res_p))
    else:
        flake_id = FlakeId(comps.geturl())
    return flake_id


# Define the ClanURI class
@dataclass
class ClanURI:
    flake: FlakeId
    machine_name: str

    def get_url(self) -> str:
        return str(self.flake)

    @classmethod
    def from_str(
        cls,  # noqa
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
        flake = _parse_url(clean_comps)
        machine_name = "defaultVM"
        if components.fragment:
            machine_name = components.fragment

        return cls(flake, machine_name)
