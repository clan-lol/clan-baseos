import ctypes
import json
import logging
import threading
from collections.abc import Callable
from enum import IntEnum
from typing import Any

from clan_cli.api import MethodRegistry, dataclass_to_dict, from_dict

from ._webview_ffi import _encode_c_string, _webview_lib

log = logging.getLogger(__name__)


class SizeHint(IntEnum):
    NONE = 0
    MIN = 1
    MAX = 2
    FIXED = 3


class Size:
    def __init__(self, width: int, height: int, hint: SizeHint) -> None:
        self.width = width
        self.height = height
        self.hint = hint


class Webview:
    def __init__(
        self, debug: bool = False, size: Size | None = None, window: int | None = None
    ) -> None:
        self._handle = _webview_lib.webview_create(int(debug), window)
        self._callbacks: dict[str, Callable[..., Any]] = {}

        if size:
            self.size = size

    @property
    def size(self) -> Size:
        return self._size

    @size.setter
    def size(self, value: Size) -> None:
        _webview_lib.webview_set_size(
            self._handle, value.width, value.height, value.hint
        )
        self._size = value

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        _webview_lib.webview_set_title(self._handle, _encode_c_string(value))
        self._title = value

    def destroy(self) -> None:
        for name in list(self._callbacks.keys()):
            self.unbind(name)
        _webview_lib.webview_terminate(self._handle)
        _webview_lib.webview_destroy(self._handle)
        self._handle = None

    def navigate(self, url: str) -> None:
        _webview_lib.webview_navigate(self._handle, _encode_c_string(url))

    def run(self) -> None:
        _webview_lib.webview_run(self._handle)
        self.destroy()

    def bind_jsonschema_api(self, api: MethodRegistry) -> None:
        for name, method in api.functions.items():

            def wrapper(
                seq: bytes,
                req: bytes,
                arg: int,
                wrap_method: Callable[..., Any] = method,
                method_name: str = name,
            ) -> None:
                def thread_task() -> None:
                    args = json.loads(req.decode())

                    try:
                        log.debug(f"Calling {method_name}({args[0]})")
                        # Initialize dataclasses from the payload
                        reconciled_arguments = {}
                        for k, v in args[0].items():
                            # Some functions expect to be called with dataclass instances
                            # But the js api returns dictionaries.
                            # Introspect the function and create the expected dataclass from dict dynamically
                            # Depending on the introspected argument_type
                            arg_class = api.get_method_argtype(method_name, k)

                            # TODO: rename from_dict into something like construct_checked_value
                            # from_dict really takes Anything and returns an instance of the type/class
                            reconciled_arguments[k] = from_dict(arg_class, v)

                        reconciled_arguments["op_key"] = seq.decode()
                        # TODO: We could remove the wrapper in the MethodRegistry
                        # and just call the method directly
                        result = wrap_method(**reconciled_arguments)
                        success = True
                    except Exception as e:
                        log.exception(f"Error calling {method_name}")
                        result = str(e)
                        success = False

                    try:
                        serialized = json.dumps(
                            dataclass_to_dict(result), indent=4, ensure_ascii=False
                        )
                    except TypeError:
                        log.exception(f"Error serializing result for {method_name}")
                        raise

                    log.debug(f"Result for {method_name}: {serialized}")
                    self.return_(seq.decode(), 0 if success else 1, serialized)

                thread = threading.Thread(target=thread_task)
                thread.start()

            c_callback = _webview_lib.CFUNCTYPE(
                None, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p
            )(wrapper)

            if name in self._callbacks:
                msg = f"Callback {name} already exists. Skipping binding."
                raise RuntimeError(msg)

            self._callbacks[name] = c_callback
            _webview_lib.webview_bind(
                self._handle, _encode_c_string(name), c_callback, None
            )

    def bind(self, name: str, callback: Callable[..., Any]) -> None:
        def wrapper(seq: bytes, req: bytes, arg: int) -> None:
            args = json.loads(req.decode())
            try:
                result = callback(*args)
                success = True
            except Exception as e:
                result = str(e)
                success = False
            self.return_(seq.decode(), 0 if success else 1, json.dumps(result))

        c_callback = _webview_lib.CFUNCTYPE(
            None, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p
        )(wrapper)
        self._callbacks[name] = c_callback
        _webview_lib.webview_bind(
            self._handle, _encode_c_string(name), c_callback, None
        )

    def unbind(self, name: str) -> None:
        if name in self._callbacks:
            _webview_lib.webview_unbind(self._handle, _encode_c_string(name))
            del self._callbacks[name]

    def return_(self, seq: str, status: int, result: str) -> None:
        _webview_lib.webview_return(
            self._handle, _encode_c_string(seq), status, _encode_c_string(result)
        )

    def eval(self, source: str) -> None:
        _webview_lib.webview_eval(self._handle, _encode_c_string(source))

    def init(self, source: str) -> None:
        _webview_lib.webview_init(self._handle, _encode_c_string(source))


if __name__ == "__main__":
    wv = Webview()
    wv.title = "Hello, World!"
    wv.navigate("https://www.google.com")
    wv.run()
