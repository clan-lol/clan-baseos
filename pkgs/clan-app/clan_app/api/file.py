# ruff: noqa: N801

import logging
from tkinter import Tk, filedialog

from clan_cli.api import ApiError, ErrorDataClass, SuccessDataClass
from clan_cli.api.directory import FileFilter, FileRequest

log = logging.getLogger(__name__)


def _apply_filters(filters: FileFilter | None) -> list[tuple[str, str]]:
    if not filters:
        return []

    filter_patterns = []

    if filters.mime_types:
        # Tkinter does not directly support MIME types, so this section can be adjusted
        # if you wish to handle them differently
        filter_patterns.extend(filters.mime_types)

    if filters.patterns:
        filter_patterns.extend(filters.patterns)

    if filters.suffixes:
        suffix_patterns = [f"*.{suffix}" for suffix in filters.suffixes]
        filter_patterns.extend(suffix_patterns)

    filter_title = filters.title if filters.title else "Custom Files"

    return [(filter_title, " ".join(filter_patterns))]


def open_file(
    file_request: FileRequest, *, op_key: str
) -> SuccessDataClass[list[str] | None] | ErrorDataClass:
    try:
        root = Tk()
        root.withdraw()  # Hide the main window
        root.attributes("-topmost", True)  # Bring the dialogs to the front

        file_paths: list[str] | None = None

        if file_request.mode == "open_file":
            file_path = filedialog.askopenfilename(
                title=file_request.title,
                initialdir=file_request.initial_folder,
                initialfile=file_request.initial_file,
                filetypes=_apply_filters(file_request.filters),
            )
            file_paths = [file_path]
        elif file_request.mode == "select_folder":
            file_path = filedialog.askdirectory(
                title=file_request.title, initialdir=file_request.initial_folder
            )
            file_paths = [file_path]
        elif file_request.mode == "save":
            file_path = filedialog.asksaveasfilename(
                title=file_request.title,
                initialdir=file_request.initial_folder,
                initialfile=file_request.initial_file,
                filetypes=_apply_filters(file_request.filters),
            )
            file_paths = [file_path]
        elif file_request.mode == "open_multiple_files":
            file_paths = list(
                filedialog.askopenfilenames(
                    title=file_request.title,
                    initialdir=file_request.initial_folder,
                    filetypes=_apply_filters(file_request.filters),
                )
            )

        if not file_paths:
            msg = "No file selected or operation canceled by the user"
            raise ValueError(msg)  # noqa: TRY301

        return SuccessDataClass(op_key, status="success", data=file_paths)

    except Exception as e:
        log.exception("Error opening file")
        return ErrorDataClass(
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
    finally:
        root.destroy()
