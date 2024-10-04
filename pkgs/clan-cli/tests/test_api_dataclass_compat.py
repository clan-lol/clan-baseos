import ast
import importlib.util
import os
import sys
from dataclasses import is_dataclass
from pathlib import Path

from clan_cli.api import API
from clan_cli.api.util import JSchemaTypeError, type_to_dict
from clan_cli.errors import ClanError


def find_dataclasses_in_directory(
    directory: Path, exclude_paths: list[str] | None = None
) -> list[tuple[Path, str]]:
    """
    Find all dataclass classes in all Python files within a nested directory.

    Args:
        directory (str): The root directory to start searching from.

    Returns:
        List[Tuple[str, str]]: A list of tuples containing the file path and the dataclass name.
    """
    if exclude_paths is None:
        exclude_paths = []
    dataclass_files = []

    excludes = [directory / d for d in exclude_paths]

    for root, _, files in os.walk(directory, topdown=False):
        for file in files:
            if not file.endswith(".py"):
                continue

            file_path = Path(root) / file

            if file_path in excludes:
                print(f"Skipping dataclass check for file: {file_path}")
                continue

            python_code = file_path.read_text()
            try:
                tree = ast.parse(python_code, filename=file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for deco in node.decorator_list:
                            if (
                                isinstance(deco, ast.Name) and deco.id == "dataclass"
                            ) or (
                                isinstance(deco, ast.Call)
                                and isinstance(deco.func, ast.Name)
                                and deco.func.id == "dataclass"
                            ):
                                dataclass_files.append((file_path, node.name))
            except (SyntaxError, UnicodeDecodeError) as e:
                print(f"Error parsing {file_path}: {e}")

    return dataclass_files


def load_dataclass_from_file(
    file_path: Path, class_name: str, root_dir: str
) -> type | None:
    """
    Load a dataclass from a given file path.

    Args:
        file_path (str): Path to the file.
        class_name (str): Name of the class to load.

    Returns:
        List[Type]: The dataclass type if found, else an empty list.
    """
    module_name = (
        os.path.relpath(file_path, root_dir).replace(os.path.sep, ".").rstrip(".py")
    )
    try:
        sys.path.insert(0, root_dir)
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec:
            msg = f"Could not load spec from file: {file_path}"
            raise ClanError(msg)

        module = importlib.util.module_from_spec(spec)
        if not module:
            msg = f"Could not create module: {file_path}"
            raise ClanError(msg)

        if not spec.loader:
            msg = f"Could not load loader from spec: {spec}"
            raise ClanError(msg)

        spec.loader.exec_module(module)

    finally:
        sys.path.pop(0)
    dataclass_type = getattr(module, class_name, None)

    if dataclass_type and is_dataclass(dataclass_type):
        return dataclass_type

    msg = f"Could not load dataclass {class_name} from file: {file_path}"
    raise ClanError(msg)


def test_all_dataclasses() -> None:
    """
    This Test ensures that all dataclasses are compatible with the API.

    It will load all dataclasses from the clan_cli directory and
    generate a JSON schema for each of them.

    It will fail if any dataclass cannot be converted to JSON schema.
    This means the dataclass in its current form is not compatible with the API.
    """

    # Excludes:
    # - API includes Type Generic wrappers, that are not known in the init file.
    excludes = [
        "api/__init__.py",
    ]

    cli_path = Path("clan_cli").resolve()
    dataclasses = find_dataclasses_in_directory(cli_path, excludes)

    for file, dataclass in dataclasses:
        print(f"checking dataclass {dataclass} in file: {file}")
        try:
            API.reset()
            dclass = load_dataclass_from_file(file, dataclass, str(cli_path.parent))
            type_to_dict(dclass)
        except JSchemaTypeError as e:
            print(f"Error loading dataclass {dataclass} from {file}: {e}")
            msg = f"""
--------------------------------------------------------------------------------
Error converting dataclass 'class {dataclass}()' from {file}

Details:
 {e}

Help:
- Converting public fields to PRIVATE by prefixing them with underscore ('_')
- Ensure all private fields are initialized the API wont provide initial values for them.
--------------------------------------------------------------------------------
"""
            raise ClanError(
                msg,
                location=__file__,
            ) from e
