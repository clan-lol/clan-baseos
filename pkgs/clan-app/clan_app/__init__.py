import argparse
import logging
import sys

from clan_cli.profiler import profile

log = logging.getLogger(__name__)

from clan_app.app import ClanAppOptions, app_run


@profile
def main(argv: list[str] = sys.argv) -> int:
    parser = argparse.ArgumentParser(description="Clan App")
    parser.add_argument(
        "--content-uri", type=str, help="The URI of the content to display"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args(argv[1:])

    app_opts = ClanAppOptions(content_uri=args.content_uri, debug=args.debug)
    app_run(app_opts)

    return 0
