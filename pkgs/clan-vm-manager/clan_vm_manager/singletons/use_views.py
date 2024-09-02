from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class ViewStack:
    """
    This is a singleton.
    It is initialized with the first call of use()

    Usage:

    ViewStack.use().set_visible()

    ViewStack.use() can also be called before the data is needed. e.g. to eliminate/reduce waiting time.

    """

    _instance: "None | ViewStack" = None
    view: Adw.ViewStack

    # Make sure the VMS class is used as a singleton
    def __init__(self) -> None:
        msg = "Call use() instead"
        raise RuntimeError(msg)

    @classmethod
    def use(cls: Any) -> "ViewStack":
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
            cls.view = Adw.ViewStack()

        return cls._instance
