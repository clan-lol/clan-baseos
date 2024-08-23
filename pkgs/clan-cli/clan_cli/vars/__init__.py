# !/usr/bin/env python3
import argparse

from ..hyperlink import help_hyperlink
from .check import register_check_parser
from .generate import register_generate_parser
from .list import register_list_parser
from .upload import register_upload_parser


# takes a (sub)parser and configures it
def register_parser(parser: argparse.ArgumentParser) -> None:
    subparser = parser.add_subparsers(
        title="command",
        description="the command to run",
        help="the command to run",
        required=True,
    )

    check_parser = subparser.add_parser(
        "check",
        help="check if vars are up to date",
        epilog=(
            """
This subcommand allows checking if all vars are up to date.

Examples:

  $ clan vars check [MACHINE]
  Will check vars for the specified machine.
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_check_parser(check_parser)

    list_parser = subparser.add_parser(
        "list",
        help="list all vars",
        epilog=(
            f"""
This subcommand allows listing all non-secret vars for a specific machine.

The resulting list will be a json string with the name of the variable as its key
and the fact itself as it's value.

This is how an example output might look like:
```
\u007b
"[FACT_NAME]": "[FACT]"
\u007d
```

Examples:

  $ clan vars list [MACHINE]
  Will list non-secret vars for the specified machine.


For more detailed information, visit: {help_hyperlink("secrets", "https://docs.clan.lol/getting-started/secrets")}
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_list_parser(list_parser)

    parser_generate = subparser.add_parser(
        "generate",
        help="(re-)generate vars for specific or all machines",
        epilog=(
            f"""
This subcommand allows control of the generation of vars.
Often this function will be invoked automatically on deploying machines,
but there are situations the user may want to have more granular control,
especially for the regeneration of certain services.

A service is an included clan-module that implements vars generation functionality.
For example the zerotier module will generate secret and public vars.
In this case the public vars will be the resulting zerotier-ip of the machine.
The secret variable will be the zerotier-identity-secret, which is used by zerotier
to prove the machine has control of the zerotier-ip.


Examples:

  $ clan vars generate
  Will generate vars for all machines.

  $ clan vars generate [MACHINE]
  Will generate vars for the specified machine.

  $ clan vars generate [MACHINE] --service [SERVICE]
  Will generate vars for the specified machine for the specified service.

  $ clan vars generate --service [SERVICE] --regenerate
  Will regenerate vars, if they are already generated for a specific service.
  This is especially useful for resetting certain passwords while leaving the rest
  of the vars for a machine in place.

For more detailed information, visit: {help_hyperlink("secrets", "https://docs.clan.lol/getting-started/secrets")}
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_generate_parser(parser_generate)

    parser_upload = subparser.add_parser(
        "upload",
        help="upload secrets for machines",
        epilog=(
            f"""
This subcommand allows uploading secrets to remote machines.

If using sops as a secret backend it will upload the private key to the machine.
If using password store it uploads all the secrets you manage to the machine.

The default backend is sops.

Examples:

  $ clan vars upload [MACHINE]
  Will upload secrets to a specific machine.

For more detailed information, visit: {help_hyperlink("secrets", "https://docs.clan.lol/getting-started/secrets")}
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_upload_parser(parser_upload)
