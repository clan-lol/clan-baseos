# ruff: noqa: N801
import gi

gi.require_version("Gtk", "4.0")

import logging
import time
from pathlib import Path
from typing import Any

from clan_cli.api import ApiError, ErrorDataClass, SuccessDataClass
from clan_cli.api.directory import FileRequest
from gi.repository import Gio, GLib, Gtk

log = logging.getLogger(__name__)


def remove_none(_list: list) -> list:
    return [i for i in _list if i is not None]


RESULT: dict[str, SuccessDataClass[list[str] | None] | ErrorDataClass] = {}


def open_file(
    file_request: FileRequest, *, op_key: str
) -> SuccessDataClass[list[str] | None] | ErrorDataClass:
    GLib.idle_add(gtk_open_file, file_request, op_key)

    while RESULT.get(op_key) is None:
        time.sleep(0.2)
    response = RESULT[op_key]
    del RESULT[op_key]
    return response


def gtk_open_file(file_request: FileRequest, op_key: str) -> bool:
    def returns(data: SuccessDataClass | ErrorDataClass) -> None:
        global RESULT
        RESULT[op_key] = data

    def on_file_select(file_dialog: Gtk.FileDialog, task: Gio.Task) -> None:
        try:
            gfile = file_dialog.open_finish(task)
            if gfile:
                selected_path = remove_none([gfile.get_path()])
                returns(
                    SuccessDataClass(
                        op_key=op_key, data=selected_path, status="success"
                    )
                )
        except Exception as e:
            log.exception("Error opening file")
            returns(
                ErrorDataClass(
                    op_key=op_key,
                    status="error",
                    errors=[
                        ApiError(
                            message=e.__class__.__name__,
                            description=str(e),
                            location=["open_file"],
                        )
                    ],
                )
            )

    def on_file_select_multiple(file_dialog: Gtk.FileDialog, task: Gio.Task) -> None:
        try:
            gfiles: Any = file_dialog.open_multiple_finish(task)
            if gfiles:
                selected_paths = remove_none([gfile.get_path() for gfile in gfiles])
                returns(
                    SuccessDataClass(
                        op_key=op_key, data=selected_paths, status="success"
                    )
                )
            else:
                returns(SuccessDataClass(op_key=op_key, data=None, status="success"))
        except Exception as e:
            log.exception("Error opening file")
            returns(
                ErrorDataClass(
                    op_key=op_key,
                    status="error",
                    errors=[
                        ApiError(
                            message=e.__class__.__name__,
                            description=str(e),
                            location=["open_file"],
                        )
                    ],
                )
            )

    def on_folder_select(file_dialog: Gtk.FileDialog, task: Gio.Task) -> None:
        try:
            gfile = file_dialog.select_folder_finish(task)
            if gfile:
                selected_path = remove_none([gfile.get_path()])
                returns(
                    SuccessDataClass(
                        op_key=op_key, data=selected_path, status="success"
                    )
                )
            else:
                returns(SuccessDataClass(op_key=op_key, data=None, status="success"))
        except Exception as e:
            log.exception("Error opening file")
            returns(
                ErrorDataClass(
                    op_key=op_key,
                    status="error",
                    errors=[
                        ApiError(
                            message=e.__class__.__name__,
                            description=str(e),
                            location=["open_file"],
                        )
                    ],
                )
            )

    def on_save_finish(file_dialog: Gtk.FileDialog, task: Gio.Task) -> None:
        try:
            gfile = file_dialog.save_finish(task)
            if gfile:
                selected_path = remove_none([gfile.get_path()])
                returns(
                    SuccessDataClass(
                        op_key=op_key, data=selected_path, status="success"
                    )
                )
            else:
                returns(SuccessDataClass(op_key=op_key, data=None, status="success"))
        except Exception as e:
            log.exception("Error opening file")
            returns(
                ErrorDataClass(
                    op_key=op_key,
                    status="error",
                    errors=[
                        ApiError(
                            message=e.__class__.__name__,
                            description=str(e),
                            location=["open_file"],
                        )
                    ],
                )
            )

    dialog = Gtk.FileDialog()

    if file_request.title:
        dialog.set_title(file_request.title)

    if file_request.filters:
        filters = Gio.ListStore.new(Gtk.FileFilter)
        file_filters = Gtk.FileFilter()

        if file_request.filters.title:
            file_filters.set_name(file_request.filters.title)

        if file_request.filters.mime_types:
            for mime in file_request.filters.mime_types:
                file_filters.add_mime_type(mime)
                filters.append(file_filters)

        if file_request.filters.patterns:
            for pattern in file_request.filters.patterns:
                file_filters.add_pattern(pattern)

        if file_request.filters.suffixes:
            for suffix in file_request.filters.suffixes:
                file_filters.add_suffix(suffix)

        filters.append(file_filters)
        dialog.set_filters(filters)

    if file_request.initial_file:
        p = Path(file_request.initial_file).expanduser()
        f = Gio.File.new_for_path(str(p))
        dialog.set_initial_file(f)

    if file_request.initial_folder:
        p = Path(file_request.initial_folder).expanduser()
        f = Gio.File.new_for_path(str(p))
        dialog.set_initial_folder(f)

    # if select_folder
    if file_request.mode == "select_folder":
        dialog.select_folder(callback=on_folder_select)
    if file_request.mode == "open_multiple_files":
        dialog.open_multiple(callback=on_file_select_multiple)
    elif file_request.mode == "open_file":
        dialog.open(callback=on_file_select)
    elif file_request.mode == "save":
        dialog.save(callback=on_save_finish)

    return GLib.SOURCE_REMOVE
