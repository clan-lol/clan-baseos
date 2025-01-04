import logging
import sys

from clan_cli.profiler import profile

log = logging.getLogger(__name__)

import argparse
import os
from pathlib import Path

from clan_cli.api import API
from clan_cli.custom_logger import setup_logging

from clan_app.deps.webview.webview import Size, SizeHint, Webview


@profile
def main(argv: list[str] = sys.argv) -> int:
    parser = argparse.ArgumentParser(description="Clan App")
    parser.add_argument(
        "--content-uri", type=str, help="The URI of the content to display"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args(argv[1:])

    if args.debug:
        setup_logging(logging.DEBUG, root_log_name=__name__.split(".")[0])
        setup_logging(logging.DEBUG, root_log_name="clan_cli")
    else:
        setup_logging(logging.INFO, root_log_name=__name__.split(".")[0])

    log.debug("Debug mode enabled")

    if args.content_uri:
        content_uri = args.content_uri
    else:
        site_index: Path = Path(os.getenv("WEBUI_PATH", ".")).resolve() / "index.html"
        content_uri = f"file://{site_index}"

    webview = Webview(debug=args.debug)
    webview.bind_jsonschema_api(API)

    webview.size = Size(1280, 1024, SizeHint.NONE)
    webview.navigate(content_uri)
    webview.run()
    return 0
