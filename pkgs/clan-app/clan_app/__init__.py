import logging
import sys

from clan_cli.profiler import profile

from clan_app.app import MainApplication

log = logging.getLogger(__name__)

from urllib.parse import quote

from clan_app.deps.webview.webview import Webview


@profile
def main(argv: list[str] = sys.argv) -> int:
    html = """
    <html>
    <body>
    <h1>Hello from Python Webview!</h1>
    </body>
    </html>
    """
    webview = Webview()
    webview.navigate(f"data:text/html,{quote(html)}")
    webview.run()
    app = MainApplication()
    return app.run(argv)
