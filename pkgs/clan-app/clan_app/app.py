import logging

from clan_cli.profiler import profile

log = logging.getLogger(__name__)


import os
from dataclasses import dataclass
from pathlib import Path

from clan_cli.api import API
from clan_cli.custom_logger import setup_logging

from clan_app.api.file import open_file
from clan_app.deps.webview.webview import Size, SizeHint, Webview


@dataclass
class ClanAppOptions:
    content_uri: str
    debug: bool


@profile
def app_run(app_opts: ClanAppOptions) -> int:
    if app_opts.debug:
        setup_logging(logging.DEBUG, root_log_name=__name__.split(".")[0])
        setup_logging(logging.DEBUG, root_log_name="clan_cli")
    else:
        setup_logging(logging.INFO, root_log_name=__name__.split(".")[0])
        setup_logging(logging.INFO, root_log_name="clan_cli")

    log.debug("Debug mode enabled")

    if app_opts.content_uri:
        content_uri = app_opts.content_uri
    else:
        site_index: Path = Path(os.getenv("WEBUI_PATH", ".")).resolve() / "index.html"
        content_uri = f"file://{site_index}"

    webview = Webview(debug=app_opts.debug)

    API.overwrite_fn(open_file)
    webview.bind_jsonschema_api(API)
    webview.size = Size(1280, 1024, SizeHint.NONE)
    webview.navigate(content_uri)
    webview.run()
    return 0
