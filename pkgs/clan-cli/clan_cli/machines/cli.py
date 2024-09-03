# !/usr/bin/env python3
import argparse

from .create import register_create_parser
from .delete import register_delete_parser
from .hardware import register_hw_generate
from .install import register_install_parser
from .list import register_list_parser
from .update import register_update_parser


# takes a (sub)parser and configures it
def register_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )

    update_parser = subparser.add_parser(
        "update",
        help="Update a machine",
        epilog=(
            """
This subcommand provides an interface to update machines managed by clan.

Examples:

  $ clan machines update [MACHINES]
  Will update the specified machine [MACHINE], if [MACHINE] is omitted, the command
  will attempt to update every configured machine.
  To exclude machines being updated `clan.deployment.requireExplicitUpdate = true;`
  can be set in the machine config.

For more detailed information, visit: https://docs.clan.lol/getting-started/deploy
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_update_parser(update_parser)

    create_parser = subparser.add_parser("create", help="Create a machine")
    register_create_parser(create_parser)

    delete_parser = subparser.add_parser("delete", help="Delete a machine")
    register_delete_parser(delete_parser)

    list_parser = subparser.add_parser(
        "list",
        help="List machines",
        epilog=(
            """
This subcommand lists all machines managed by this clan.

Examples:

  $ clan machines list
  Lists all the machines and their descriptions.
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_list_parser(list_parser)

    generate_hw_parser = subparser.add_parser(
        "hw-generate",
        help="Generate hardware specifics for a machine",
        description="""
Generates hardware specifics for a machine. Such as the host platform, available kernel modules, etc.

The target must be a Linux based system reachable via SSH.
        """,
        epilog=(
            """
Examples:

  $ clan machines hw-generate [MACHINE] [TARGET_HOST]
  Will generate hardware specifics for the the specified `[TARGET_HOST]` and place the result in hardware.nix for the given machine `[MACHINE]`.

For more detailed information, visit: https://docs.clan.lol/getting-started/configure/#machine-configuration

"""
        ),
    )
    register_hw_generate(generate_hw_parser)

    install_parser = subparser.add_parser(
        "install",
        help="Install a machine",
        description="""
Install a configured machine over the network.
The target must be a Linux based system reachable via SSH.
Installing a machine means overwriting the target's disk.
        """,
        epilog=(
            """
This subcommand provides an interface to install machines managed by clan.

Examples:

  $ clan machines install [MACHINE] [TARGET_HOST]
  Will install the specified machine [MACHINE], to the specified [TARGET_HOST].

  $ clan machines install [MACHINE] --json [JSON]
  Will install the specified machine [MACHINE] to the host exposed by
  the deployment information of the [JSON] deployment string.

For information on how to set up the installer see: https://docs.clan.lol/getting-started/installer/
For more detailed information, visit: https://docs.clan.lol/getting-started/deploy
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_install_parser(install_parser)
