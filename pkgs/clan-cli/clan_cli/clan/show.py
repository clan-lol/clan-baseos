import argparse
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from clan_cli.api import API
from clan_cli.cmd import run_no_stdout
from clan_cli.errors import ClanCmdError, ClanError
from clan_cli.inventory import Meta
from clan_cli.nix import nix_eval

log = logging.getLogger(__name__)


@API.register
def show_clan_meta(uri: str | Path) -> Meta:
    cmd = nix_eval(
        [
            f"{uri}#clanInternals.inventory.meta",
            "--json",
        ]
    )
    res = "{}"

    try:
        proc = run_no_stdout(cmd)
        res = proc.stdout.strip()
    except ClanCmdError as e:
        raise ClanError(
            "Evaluation failed on meta attribute",
            location=f"show_clan {uri}",
            description=str(e.cmd),
        ) from e

    clan_meta = json.loads(res)

    # Check if icon is a URL such as http:// or https://
    # Check if icon is an relative path
    # All other schemas such as file://, ftp:// are not yet supported.
    icon_path: str | None = None
    if meta_icon := clan_meta.get("icon"):
        scheme = urlparse(meta_icon).scheme
        if scheme in ["http", "https"]:
            icon_path = meta_icon
        elif scheme in [""]:
            if Path(meta_icon).is_absolute():
                raise ClanError(
                    "Invalid absolute path",
                    location=f"show_clan {uri}",
                    description="Icon path must be a URL or a relative path.",
                )

            else:
                icon_path = str((Path(uri) / meta_icon).resolve())
        else:
            raise ClanError(
                "Invalid schema",
                location=f"show_clan {uri}",
                description="Icon path must be a URL or a relative path.",
            )

    return Meta(
        name=clan_meta.get("name"),
        description=clan_meta.get("description", None),
        icon=icon_path,
    )


def show_command(args: argparse.Namespace) -> None:
    flake_path = args.flake.path
    meta = show_clan_meta(flake_path)

    print(f"Name: {meta.name}")
    print(f"Description: {meta.description or '-'}")
    print(f"Icon: {meta.icon or '-'}")


def register_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=show_command)
    parser.add_argument(
        "show",
        help="Show",
    )
