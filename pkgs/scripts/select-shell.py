import argparse
import json
import os
import pathlib
import subprocess
import sys

selected_shell_file = pathlib.Path(".direnv/selected-shell")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select a devshell")
    parser.add_argument("shell", help="the name of the devshell to select", nargs="?")
    parser.add_argument("--list", action="store_true", help="list available devshells")
    parser.add_argument(
        "--show", action="store_true", help="show the currently selected devshell"
    )
    return parser.parse_args()


def get_current_shell() -> str | None:
    if selected_shell_file.exists():
        return selected_shell_file.read_text().strip()
    return None


def print_current_shell() -> None:
    current_shell = get_current_shell()
    if current_shell:
        print(f"Currently selected devshell: {current_shell}")
    else:
        print("No devshell selected")


def list_devshells() -> list[str]:
    project_root = os.environ.get("PRJ_ROOT")
    flake_show = subprocess.run(
        [
            "nix",
            "eval",
            "--json",
            "--apply",
            "shells: builtins.mapAttrs (name: _shell: name) shells",
            f"{project_root}#devShells.x86_64-linux",
        ],
        stdout=subprocess.PIPE,
        check=True,
    )
    names = json.loads(flake_show.stdout.decode())
    return names


def print_devshells() -> None:
    names = list_devshells()
    print("Available devshells:")
    print("\n".join(names))


def select_shell(shell: str) -> None:
    if shell == get_current_shell():
        print(f"{shell} devshell already selected. No changes made.")
        sys.exit(0)
    elif shell not in (names := list_devshells()):
        print(f"devshell '{shell}' not found. Available devshells:")
        print("\n".join(names))
    else:
        with selected_shell_file.open("w") as f:
            f.write(shell)
        print(f"{shell} devshell selected")


def main() -> None:
    args = parse_args()
    if args.show:
        print_current_shell()
    elif args.list:
        print_devshells()
    elif args.shell:
        select_shell(args.shell)
    else:
        print_current_shell()
        print("Use --help for more information")


if __name__ == "__main__":
    main()
