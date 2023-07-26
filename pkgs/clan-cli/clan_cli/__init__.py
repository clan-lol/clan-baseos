# !/usr/bin/env python3
import argparse
import sys

from . import admin, ssh

has_argcomplete = True
try:
    import argcomplete
except ImportError:  # pragma: no cover
    has_argcomplete = False


# this will be the entrypoint under /bin/clan (see pyproject.toml config)
def main() -> None:
    parser = argparse.ArgumentParser(description="cLAN tool")
    subparsers = parser.add_subparsers()

    parser_admin = subparsers.add_parser("admin")
    admin.register_parser(parser_admin)

    parser_ssh = subparsers.add_parser("ssh", help="ssh to a remote machine")
    ssh.register_parser(parser_ssh)

    if has_argcomplete:
        argcomplete.autocomplete(parser)

    if len(sys.argv) == 1:
        parser.print_help()

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)  # pragma: no cover


if __name__ == "__main__":  # pragma: no cover
    main()
