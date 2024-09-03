import logging
from collections.abc import Callable
from typing import TypeVar

import gi

from clan_vm_manager import assets

gi.require_version("Adw", "1")
from gi.repository import Adw, GdkPixbuf, Gio, GObject, Gtk

log = logging.getLogger(__name__)

ListItem = TypeVar("ListItem", bound=GObject.Object)
CustomStore = TypeVar("CustomStore", bound=Gio.ListModel)


class EmptySplash(Gtk.Box):
    def __init__(self, on_join: Callable[[str], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.on_join = on_join

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        clan_icon = self.load_image(str(assets.get_asset("clan_black_notext.png")))

        if clan_icon:
            image = Gtk.Image.new_from_pixbuf(clan_icon)
        else:
            image = Gtk.Image.new_from_icon_name("image-missing")
        # same as the clamp
        image.set_pixel_size(400)
        image.set_opacity(0.5)
        image.set_margin_top(20)
        image.set_margin_bottom(10)

        vbox.append(image)

        empty_label = Gtk.Label(label="Welcome to Clan! Join your first clan.")
        join_entry = Gtk.Entry()
        join_entry.set_placeholder_text("clan://<url>")
        join_entry.set_hexpand(True)

        join_button = Gtk.Button(label="Join")
        join_button.connect("clicked", self._on_join, join_entry)

        join_entry.connect("activate", lambda e: self._on_join(join_button, e))

        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_bottom(40)
        vbox.append(empty_label)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hbox.append(join_entry)
        hbox.append(join_button)
        vbox.append(hbox)
        clamp.set_child(vbox)

        self.append(clamp)

    def load_image(self, file_path: str) -> GdkPixbuf.Pixbuf | None:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(file_path)
        except Exception:
            log.exception("Failed to load image")
            return None
        else:
            return pixbuf

    def _on_join(self, button: Gtk.Button, entry: Gtk.Entry) -> None:
        """
        Callback for the join button
        Extracts the text from the entry and calls the on_join callback
        """
        log.info(f"Splash screen: Joining {entry.get_text()}")
        self.on_join(entry.get_text())
