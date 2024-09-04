import base64
import logging
from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

import gi
from clan_cli.clan_uri import ClanURI
from clan_cli.errors import ClanError

from clan_vm_manager.components.gkvstore import GKVStore
from clan_vm_manager.components.interfaces import ClanConfig
from clan_vm_manager.components.list_splash import EmptySplash
from clan_vm_manager.components.vmobj import VMObject
from clan_vm_manager.singletons.toast import (
    LogToast,
    SuccessToast,
    ToastOverlay,
    WarningToast,
)
from clan_vm_manager.singletons.use_join import JoinList, JoinValue
from clan_vm_manager.singletons.use_views import ViewStack
from clan_vm_manager.singletons.use_vms import ClanStore, VMStore
from clan_vm_manager.views.logs import Logs

gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

log = logging.getLogger(__name__)

ListItem = TypeVar("ListItem", bound=GObject.Object)
CustomStore = TypeVar("CustomStore", bound=Gio.ListModel)


def create_boxed_list(
    model: CustomStore,
    render_row: Callable[[Gtk.ListBox, ListItem], Gtk.Widget],
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

        app = Gio.Application.get_default()
        assert app is not None
        app.connect("join_request", self.on_join_request)

        self.log_label: Gtk.Label = Gtk.Label()

        # Add join list
        self.join_boxed_list = create_boxed_list(
            model=JoinList.use().list_store, render_row=self.render_join_row
        )
        self.join_boxed_list.add_css_class("join-list")
        self.append(self.join_boxed_list)

        clan_store = ClanStore.use()
        clan_store.connect("is_ready", self.display_splash)

        self.group_list = create_boxed_list(
            model=clan_store.clan_store, render_row=self.render_group_row
        )
        self.group_list.add_css_class("group-list")
        self.append(self.group_list)

        self.splash = EmptySplash(on_join=lambda x: self.on_join_request(x, x))

    def display_splash(self, source: GKVStore) -> None:
        print("Displaying splash")
        if (
            ClanStore.use().clan_store.get_n_items() == 0
            and JoinList.use().list_store.get_n_items() == 0
        ):
            self.append(self.splash)

    def render_group_row(
        self, boxed_list: Gtk.ListBox, vm_store: VMStore
    ) -> Gtk.Widget:
        self.remove(self.splash)

        vm = vm_store.first()
        log.debug("Rendering group row for %s", vm.data.flake.flake_url)

        grp = Adw.PreferencesGroup()
        grp.set_title(vm.data.flake.clan_name)
        grp.set_description(str(vm.data.flake.flake_url))

        add_action = Gio.SimpleAction.new("add", GLib.VariantType.new("s"))
        add_action.connect("activate", self.on_add)
        app = Gio.Application.get_default()
        assert app is not None
        app.add_action(add_action)

        # menu_model = Gio.Menu()
        # TODO: Make this lazy, blocks UI startup for too long
        # for vm in machines.list.list_nixos_machines(flake_url=vm.data.flake.flake_url):
        #     if vm not in vm_store:
        #         menu_model.append(vm, f"app.add::{vm}")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_valign(Gtk.Align.CENTER)

        add_button = Gtk.Button()
        add_button_content = Adw.ButtonContent.new()
        add_button_content.set_label("Add machine")
        add_button_content.set_icon_name("list-add-symbolic")
        add_button.add_css_class("flat")
        add_button.set_child(add_button_content)

        # add_button.set_has_frame(False)
        # add_button.set_menu_model(menu_model)
        # add_button.set_label("Add machine")
        box.append(add_button)

        grp.set_header_suffix(box)

        vm_list = create_boxed_list(model=vm_store, render_row=self.render_vm_row)
        grp.add(vm_list)

        return grp

    def on_add(self, source: Any, parameter: Any) -> None:
        target = parameter.get_string()
        print("Adding new machine", target)

    def render_vm_row(self, boxed_list: Gtk.ListBox, vm: VMObject) -> Gtk.Widget:
        # Remove no-shadow class if attached
        if boxed_list.has_css_class("no-shadow"):
            boxed_list.remove_css_class("no-shadow")
        flake = vm.data.flake
        row = Adw.ActionRow()

        # ====== Display Avatar ======
        avatar = Adw.Avatar()
        machine_icon = flake.vm.machine_icon

        # If there is a machine icon, display it else
        # display the clan icon
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

        # If there is a machine description, display it else
        # display the clan name
        if flake.vm.machine_description:
            row.set_subtitle(flake.vm.machine_description)
        else:
            row.set_subtitle(flake.clan_name)
        row.set_subtitle_lines(1)

        # ==== Display build progress bar ====
        build_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        build_box.set_valign(Gtk.Align.CENTER)
        build_box.append(vm.progress_bar)
        build_box.set_homogeneous(False)
        row.add_suffix(build_box)  # This allows children to have different sizes

        # ==== Action buttons ====
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        button_box.set_valign(Gtk.Align.CENTER)

        ## Drop down menu
        open_action = Gio.SimpleAction.new("edit", GLib.VariantType.new("s"))
        open_action.connect("activate", self.on_edit)

        action_id = base64.b64encode(vm.get_id().encode("utf-8")).decode("utf-8")

        build_logs_action = Gio.SimpleAction.new(
            f"logs.{action_id}", GLib.VariantType.new("s")
        )

        build_logs_action.connect("activate", self.on_show_build_logs)
        build_logs_action.set_enabled(False)

        app = Gio.Application.get_default()
        assert app is not None

        app.add_action(open_action)
        app.add_action(build_logs_action)

        # set a callback function for conditionally enabling the build_logs action
        def on_vm_build_notify(
            vm: VMObject, is_building: bool, is_running: bool
        ) -> None:
            build_logs_action.set_enabled(is_building or is_running)
            app.add_action(build_logs_action)
            if is_building:
                ToastOverlay.use().add_toast_unique(
                    LogToast(
                        """Build process running ...""",
                        on_button_click=lambda: self.show_vm_build_logs(vm.get_id()),
                    ).toast,
                    f"info.build.running.{vm}",
                )

        vm.connect("vm_build_notify", on_vm_build_notify)

        menu_model = Gio.Menu()
        menu_model.append("Edit", f"app.edit::{vm.get_id()}")
        menu_model.append("Show Logs", f"app.logs.{action_id}::{vm.get_id()}")

        pref_button = Gtk.MenuButton()
        pref_button.set_icon_name("open-menu-symbolic")
        pref_button.set_menu_model(menu_model)

        button_box.append(pref_button)

        ## VM switch button
        switch_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        switch_box.set_valign(Gtk.Align.CENTER)
        switch_box.append(vm.switch)
        button_box.append(switch_box)

        row.add_suffix(button_box)

        return row

    def on_edit(self, source: Any, parameter: Any) -> None:
        target = parameter.get_string()
        print("Editing settings for machine", target)

    def on_show_build_logs(self, _: Any, parameter: Any) -> None:
        target = parameter.get_string()
        self.show_vm_build_logs(target)

    def show_vm_build_logs(self, target: str) -> None:
        vm = ClanStore.use().set_logging_vm(target)
        if vm is None:
            msg = f"VM {target} not found"
            raise ClanError(msg)

        views = ViewStack.use().view
        # Reset the logs view
        logs: Logs = views.get_child_by_name("logs")  # type: ignore

        if logs is None:
            msg = "Logs view not found"
            raise ClanError(msg)

        name = vm.machine.name if vm.machine else "Unknown"

        logs.set_title(f"""📄<span weight="normal"> {name}</span>""")
        # initial message. Streaming happens automatically when the file is changed by the build process
        logs.set_message(vm.build_process.out_file.read_text())

        views.set_visible_child_name("logs")

    def render_join_row(
        self, boxed_list: Gtk.ListBox, join_val: JoinValue
    ) -> Gtk.Widget:
        if boxed_list.has_css_class("no-shadow"):
            boxed_list.remove_css_class("no-shadow")

        log.debug("Rendering join row for %s", join_val.url)

        row = Adw.ActionRow()
        row.set_title(join_val.url.machine_name)
        row.set_subtitle(str(join_val.url))
        row.add_css_class("trust")

        vm = ClanStore.use().get_vm(join_val.url)

        # Can't do this here because clan store is empty at this point
        if vm is not None:
            sub = row.get_subtitle()
            assert sub is not None

            ToastOverlay.use().add_toast_unique(
                WarningToast(
                    f"""<span weight="regular">{join_val.url.machine_name!s}</span> Already exists. Joining again will update it"""
                ).toast,
                "warning.duplicate.join",
            )

            row.set_subtitle(
                sub + "\nClan already exists. Joining again will update it"
            )

        avatar = Adw.Avatar()
        avatar.set_text(str(join_val.url.machine_name))
        avatar.set_show_initials(True)
        avatar.set_size(50)
        row.add_prefix(avatar)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.add_css_class("error")
        cancel_button.connect("clicked", partial(self.on_discard_clicked, join_val))
        self.cancel_button = cancel_button

        trust_button = Gtk.Button(label="Join")
        trust_button.add_css_class("success")
        trust_button.connect("clicked", partial(self.on_trust_clicked, join_val))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_valign(Gtk.Align.CENTER)
        box.append(cancel_button)
        box.append(trust_button)

        row.add_suffix(box)

        return row

    def on_join_request(self, source: Any, url: str) -> None:
        log.debug("Join request: %s", url)
        clan_uri = ClanURI(url)
        JoinList.use().push(clan_uri, self.on_after_join)

    def on_after_join(self, source: JoinValue) -> None:
        ToastOverlay.use().add_toast_unique(
            SuccessToast(f"Updated {source.url.machine_name}").toast,
            "success.join",
        )
        # If the join request list is empty disable the shadow artefact
        if JoinList.use().is_empty():
            self.join_boxed_list.add_css_class("no-shadow")

    def on_trust_clicked(self, value: JoinValue, source: Gtk.Widget) -> None:
        source.set_sensitive(False)
        self.cancel_button.set_sensitive(False)
        value.join()

    def on_discard_clicked(self, value: JoinValue, source: Gtk.Widget) -> None:
        JoinList.use().discard(value)
        if JoinList.use().is_empty():
            self.join_boxed_list.add_css_class("no-shadow")
