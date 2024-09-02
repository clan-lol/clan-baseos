import logging
from collections.abc import Callable
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw

log = logging.getLogger(__name__)


class ToastOverlay:
    """
    The ToastOverlay is a class that manages the display of toasts
    It should be used as a singleton in your application to prevent duplicate toasts
    Usage
    """

    # For some reason, the adw toast overlay cannot be subclassed
    # Thats why it is added as a class property
    overlay: Adw.ToastOverlay
    active_toasts: set[str]

    _instance: "None | ToastOverlay" = None

    def __init__(self) -> None:
        msg = "Call use() instead"
        raise RuntimeError(msg)

    @classmethod
    def use(cls: Any) -> "ToastOverlay":
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls.overlay = Adw.ToastOverlay()
            cls.active_toasts = set()

        return cls._instance

    def add_toast_unique(self, toast: Adw.Toast, key: str) -> None:
        if key not in self.active_toasts:
            self.active_toasts.add(key)
            self.overlay.add_toast(toast)
            toast.connect("dismissed", lambda toast: self.active_toasts.remove(key))


class WarningToast:
    toast: Adw.Toast

    def __init__(self, message: str, persistent: bool = False) -> None:
        super().__init__()
        self.toast = Adw.Toast.new(
            f"<span foreground='orange'>⚠ Warning </span> {message}"
        )
        self.toast.set_use_markup(True)

        self.toast.set_priority(Adw.ToastPriority.NORMAL)

        if persistent:
            self.toast.set_timeout(0)


class InfoToast:
    toast: Adw.Toast

    def __init__(self, message: str, persistent: bool = False) -> None:
        super().__init__()
        self.toast = Adw.Toast.new(f"<span>❕</span> {message}")
        self.toast.set_use_markup(True)

        self.toast.set_priority(Adw.ToastPriority.NORMAL)

        if persistent:
            self.toast.set_timeout(0)


class SuccessToast:
    toast: Adw.Toast

    def __init__(self, message: str, persistent: bool = False) -> None:
        super().__init__()
        self.toast = Adw.Toast.new(f"<span foreground='green'>✅</span> {message}")
        self.toast.set_use_markup(True)

        self.toast.set_priority(Adw.ToastPriority.NORMAL)

        if persistent:
            self.toast.set_timeout(0)


class LogToast:
    toast: Adw.Toast

    def __init__(
        self,
        message: str,
        on_button_click: Callable[[], None],
        button_label: str = "More",
        persistent: bool = False,
    ) -> None:
        super().__init__()
        self.toast = Adw.Toast.new(
            f"""Logs are available <span weight="regular">{message}</span>"""
        )
        self.toast.set_use_markup(True)

        self.toast.set_priority(Adw.ToastPriority.NORMAL)

        if persistent:
            self.toast.set_timeout(0)

        self.toast.set_button_label(button_label)
        self.toast.connect(
            "button-clicked",
            lambda _: on_button_click(),
        )
