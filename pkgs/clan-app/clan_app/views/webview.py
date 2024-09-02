import json
import logging
from typing import Any

import gi
from clan_cli.api import MethodRegistry, dataclass_to_dict, from_dict

from clan_app.api import GObjApi, GResult, ImplFunc
from clan_app.api.file import open_file

gi.require_version("WebKit", "6.0")
from gi.repository import GLib, GObject, WebKit

log = logging.getLogger(__name__)


class WebExecutor(GObject.Object):
    def __init__(self, content_uri: str, jschema_api: MethodRegistry) -> None:
        super().__init__()
        self.jschema_api: MethodRegistry = jschema_api
        self.webview: WebKit.WebView = WebKit.WebView()

        settings: WebKit.Settings = self.webview.get_settings()
        # settings.
        settings.set_property("enable-developer-extras", True)
        self.webview.set_settings(settings)
        # FIXME: This filtering is incomplete, it only triggers if a user clicks a link
        self.webview.connect("decide-policy", self.on_decide_policy)
        # For when the page is fully loaded
        self.webview.connect("load-changed", self.on_load_changed)
        self.manager: WebKit.UserContentManager = (
            self.webview.get_user_content_manager()
        )
        # Can be called with: window.webkit.messageHandlers.gtk.postMessage("...")
        # Important: it seems postMessage must be given some payload, otherwise it won't trigger the event
        self.manager.register_script_message_handler("gtk")
        self.manager.connect("script-message-received", self.on_message_received)

        self.webview.load_uri(content_uri)
        self.content_uri = content_uri

        self.api: GObjApi = GObjApi(self.jschema_api.functions)

        self.api.overwrite_fn(open_file)
        self.api.check_signature(self.jschema_api.signatures)

    def on_load_changed(
        self, webview: WebKit.WebView, load_event: WebKit.LoadEvent
    ) -> None:
        if load_event == WebKit.LoadEvent.FINISHED:
            if log.isEnabledFor(logging.DEBUG):
                inspector = webview.get_inspector()
                inspector.show()

    def on_decide_policy(
        self,
        webview: WebKit.WebView,
        decision: WebKit.NavigationPolicyDecision,
        decision_type: WebKit.PolicyDecisionType,
    ) -> bool:
        if decision_type != WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            return False  # Continue with the default handler

        navigation_action: WebKit.NavigationAction = decision.get_navigation_action()
        request: WebKit.URIRequest = navigation_action.get_request()
        uri = request.get_uri()
        if self.content_uri.startswith("http://") and uri.startswith(self.content_uri):
            log.debug(f"Allow navigation request: {uri}")
            return False
        if self.content_uri.startswith("file://") and uri.startswith(self.content_uri):
            log.debug(f"Allow navigation request: {uri}")
            return False
        log.warning(
            f"Do not allow navigation request: {uri}. Current content uri: {self.content_uri}"
        )
        decision.ignore()
        return True  # Stop other handlers from being invoked

    def on_message_received(
        self, user_content_manager: WebKit.UserContentManager, message: Any
    ) -> None:
        json_msg = message.to_json(4)  # 4 is num of indents
        log.debug(f"Webview Request: {json_msg}")
        payload = json.loads(json_msg)
        method_name = payload["method"]

        # Get the function gobject from the api
        function_obj = self.api.get_obj(method_name)

        # Create an instance of the function gobject
        fn_instance = function_obj()
        fn_instance.await_result(self.on_result)

        # Extract the data from the payload
        data = payload.get("data")
        if data is None:
            log.error(
                f"JS function call '{method_name}' has no data field. Skipping execution."
            )
            return

        if data.get("op_key") is None:
            log.error(
                f"JS function call '{method_name}' has no op_key field. Skipping execution."
            )
            return

        # Initialize dataclasses from the payload
        reconciled_arguments = {}
        for k, v in data.items():
            # Some functions expect to be called with dataclass instances
            # But the js api returns dictionaries.
            # Introspect the function and create the expected dataclass from dict dynamically
            # Depending on the introspected argument_type
            arg_class = self.jschema_api.get_method_argtype(method_name, k)

            # TODO: rename from_dict into something like construct_checked_value
            # from_dict really takes Anything and returns an instance of the type/class
            reconciled_arguments[k] = from_dict(arg_class, v)

        GLib.idle_add(fn_instance.internal_async_run, reconciled_arguments)

    def on_result(self, source: ImplFunc, data: GResult) -> None:
        result = dataclass_to_dict(data.result)
        serialized = json.dumps(result, indent=4)
        log.debug(f"Result for {data.method_name}: {serialized}")

        # Use idle_add to queue the response call to js on the main GTK thread
        self.return_data_to_js(data.method_name, serialized)

    def return_data_to_js(self, method_name: str, serialized: str) -> bool:
        self.webview.evaluate_javascript(
            f"""
            window.clan.{method_name}(`{serialized}`);
            """,
            -1,
            None,
            None,
            None,
        )
        return GLib.SOURCE_REMOVE

    def get_webview(self) -> WebKit.WebView:
        return self.webview
