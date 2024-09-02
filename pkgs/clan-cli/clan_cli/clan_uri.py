# Import the urllib.parse, enum and dataclasses modules
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .errors import ClanError


@dataclass
class FlakeId:
    loc: str

    def __post_init__(self) -> None:
        assert isinstance(
            self.loc, str
        ), f"Flake {self.loc} has an invalid format: {type(self.loc)}"

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
        if x.scheme == "" or "file" in x.scheme:
            # See above *file* or empty are the only local schemas
            return True

        return False

    def is_remote(self) -> bool:
        return not self.is_local()


# Define the ClanURI class
@dataclass
class ClanURI:
    flake: FlakeId
    machine_name: str

    # Initialize the class with a clan:// URI
    def __init__(self, uri: str) -> None:
        # users might copy whitespace along with the uri
        uri = uri.strip()
        self._orig_uri = uri

        # Check if the URI starts with clan://
        # If it does, remove the clan:// prefix
        if uri.startswith("clan://"):
            nested_uri = uri[7:]
        else:
            msg = f"Invalid uri: expected clan://, got {uri}"
            raise ClanError(msg)

        # Parse the URI into components
        # url://netloc/path;parameters?query#fragment
        components: urllib.parse.ParseResult = urllib.parse.urlparse(nested_uri)

        # Replace the query string in the components with the new query string
        clean_comps = components._replace(query=components.query, fragment="")

        # Parse the URL into a ClanUrl object
        self.flake = self._parse_url(clean_comps)
        self.machine_name = "defaultVM"
        if components.fragment:
            self.machine_name = components.fragment

    def _parse_url(self, comps: urllib.parse.ParseResult) -> FlakeId:
        if comps.scheme == "" or "file" in comps.scheme:
            res_p = Path(comps.path).expanduser().resolve()
            flake_id = FlakeId(str(res_p))
        else:
            flake_id = FlakeId(comps.geturl())
        return flake_id

    def get_url(self) -> str:
        return str(self.flake)

    @classmethod
    def from_str(
        cls,  # noqa
        url: str,
        machine_name: str | None = None,
    ) -> "ClanURI":
        clan_uri = ""
        if not url.startswith("clan://"):
            clan_uri += "clan://"

        clan_uri += url

        if machine_name:
            clan_uri += f"#{machine_name}"

        return cls(clan_uri)
