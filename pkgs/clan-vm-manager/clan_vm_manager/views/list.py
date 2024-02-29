import logging
from collections.abc import Callable
from functools import partial
from typing import Any

import gi
from clan_cli import history, machines
from clan_cli.clan_uri import ClanURI

from clan_vm_manager.models.interfaces import ClanConfig
from clan_vm_manager.models.use_join import Join, JoinValue
from clan_vm_manager.models.use_vms import VM, VMs, VMStore

gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

log = logging.getLogger(__name__)


def create_boxed_list(
    model: Gio.ListStore, render_row: Callable[[Gtk.ListBox, GObject], Gtk.Widget]
) -> Gtk.ListBox:
    boxed_list = Gtk.ListBox()
    boxed_list.set_selection_mode(Gtk.SelectionMode.NONE)
    boxed_list.add_css_class("boxed-list")
    boxed_list.add_css_class("no-shadow")

    boxed_list.bind_model(model, create_widget_func=partial(render_row, boxed_list))
    return boxed_list


class ClanList(Gtk.Box):
    """
    The ClanList
    Is the composition of
    the ClanListToolbar
    the clanListView
    # ------------------------        #
    # - Tools <Start> <Stop> < Edit>  #
    # ------------------------        #
    # - List Items
    # - <...>
    # ------------------------#
    """

    def __init__(self, config: ClanConfig) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.app = Gio.Application.get_default()
        self.app.connect("join_request", self.on_join_request)

        self.log_label: Gtk.Label = Gtk.Label()
        self.__init_machines = history.add.list_history()

        # Add join list
        self.join_boxed_list = create_boxed_list(
            model=Join.use().list_store, render_row=self.render_join_row
        )
        self.join_boxed_list.add_css_class("join-list")
        self.append(self.join_boxed_list)

        self.group_list = create_boxed_list(
            model=VMs.use().clan_store, render_row=self.render_group_row
        )
        self.group_list.add_css_class("group-list")
        self.append(self.group_list)

    def render_group_row(
        self, boxed_list: Gtk.ListBox, vm_store: VMStore
    ) -> Gtk.Widget:
        vm = vm_store.first()
        log.debug("Rendering group row for %s", vm.data.flake.flake_url)
        grp = Adw.PreferencesGroup()
        grp.set_title(vm.data.flake.clan_name)
        grp.set_description(vm.data.flake.flake_url)

        add_action = Gio.SimpleAction.new("add", GLib.VariantType.new("s"))
        add_action.connect("activate", self.on_add)
        app = Gio.Application.get_default()
        app.add_action(add_action)

        menu_model = Gio.Menu()
        for vm in machines.list.list_machines(flake_url=vm.data.flake.flake_url):
            if vm not in vm_store:
                menu_model.append(vm, f"app.add::{vm}")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_valign(Gtk.Align.CENTER)

        add_button = Gtk.MenuButton()
        add_button.set_has_frame(False)
        add_button.set_menu_model(menu_model)
        add_button.set_label("Add machine")
        box.append(add_button)

        grp.set_header_suffix(box)

        vm_list = create_boxed_list(model=vm_store, render_row=self.render_vm_row)
        grp.add(vm_list)

        return grp

    def on_add(self, action: Any, parameter: Any) -> None:
        target = parameter.get_string()
        print("Adding new machine", target)

    def render_vm_row(self, boxed_list: Gtk.ListBox, vm: VM) -> Gtk.Widget:
        # Remove no-shadow class if attached
        if boxed_list.has_css_class("no-shadow"):
            boxed_list.remove_css_class("no-shadow")
        flake = vm.data.flake
        row = Adw.ActionRow()

        # ====== Display Avatar ======
        avatar = Adw.Avatar()

        machine_icon = flake.vm.machine_icon
        if machine_icon:
            avatar.set_custom_image(Gdk.Texture.new_from_filename(str(machine_icon)))
        elif flake.icon:
            avatar.set_custom_image(Gdk.Texture.new_from_filename(str(flake.icon)))
        else:
            avatar.set_text(flake.clan_name + " " + flake.flake_attr)

        avatar.set_show_initials(True)
        avatar.set_size(50)
        row.add_prefix(avatar)

        # ====== Display Name And Url =====
        row.set_title(flake.flake_attr)

        row.set_title_lines(1)
        row.set_title_selectable(True)

        if flake.vm.machine_description:
            row.set_subtitle(flake.vm.machine_description)
        else:
            row.set_subtitle(flake.clan_name)
        row.set_subtitle_lines(1)

        # ==== Display build progress bar ====
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_valign(Gtk.Align.CENTER)
        box.append(vm.progress_bar)
        box.set_homogeneous(False)
        row.add_suffix(box)  # This allows children to have different sizes

        # ==== Action buttons ====
        switch_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        switch_box.set_valign(Gtk.Align.CENTER)
        switch_box.append(vm.switch)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_valign(Gtk.Align.CENTER)

        open_action = Gio.SimpleAction.new("edit", GLib.VariantType.new("s"))
        open_action.connect("activate", self.on_edit)

        app = Gio.Application.get_default()
        app.add_action(open_action)

        menu_model = Gio.Menu()
        menu_model.append("Edit", f"app.edit::{vm.get_id()}")
        pref_button = Gtk.MenuButton()
        pref_button.set_icon_name("open-menu-symbolic")
        pref_button.set_menu_model(menu_model)

        box.append(switch_box)
        box.append(pref_button)

        # suffix.append(box)
        row.add_suffix(box)

        return row

    def on_edit(self, action: Any, parameter: Any) -> None:
        target = parameter.get_string()

        print("Editing settings for machine", target)

    def render_join_row(self, boxed_list: Gtk.ListBox, item: JoinValue) -> Gtk.Widget:
        if boxed_list.has_css_class("no-shadow"):
            boxed_list.remove_css_class("no-shadow")

        row = Adw.ActionRow()

        row.set_title(item.url.params.flake_attr)
        row.set_subtitle(item.url.get_internal())
        row.add_css_class("trust")

        if item.url.params.flake_attr in VMs.use().clan_store:
            sub = row.get_subtitle()
            row.set_subtitle(
                sub + "\nClan already exists. Joining again will update it"
            )

        avatar = Adw.Avatar()
        avatar.set_text(str(item.url.params.flake_attr))
        avatar.set_show_initials(True)
        avatar.set_size(50)
        row.add_prefix(avatar)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.add_css_class("error")
        cancel_button.connect("clicked", partial(self.on_discard_clicked, item))
        self.cancel_button = cancel_button

        trust_button = Gtk.Button(label="Join")
        trust_button.add_css_class("success")
        trust_button.connect("clicked", partial(self.on_trust_clicked, item))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_valign(Gtk.Align.CENTER)
        box.append(cancel_button)
        box.append(trust_button)

        row.add_suffix(box)

        return row

    def on_join_request(self, widget: Any, url: str) -> None:
        log.debug("Join request: %s", url)
        clan_uri = ClanURI.from_str(url)
        Join.use().push(clan_uri, self.after_join)

    def after_join(self, item: JoinValue) -> None:
        # If the join request list is empty disable the shadow artefact
        if not Join.use().list_store.get_n_items():
            self.join_boxed_list.add_css_class("no-shadow")
        print("after join in list")

    def on_trust_clicked(self, item: JoinValue, widget: Gtk.Widget) -> None:
        widget.set_sensitive(False)
        self.cancel_button.set_sensitive(False)

        # TODO(@hsjobeki): Confirm and edit details
        # Views.use().view.set_visible_child_name("details")

        Join.use().join(item)

    def on_discard_clicked(self, item: JoinValue, widget: Gtk.Widget) -> None:
        Join.use().discard(item)
        if not Join.use().list_store.get_n_items():
            self.join_boxed_list.add_css_class("no-shadow")
