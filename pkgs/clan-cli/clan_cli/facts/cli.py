# !/usr/bin/env python3
import argparse

from clan_cli.hyperlink import help_hyperlink

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
        help="check if facts are up to date",
        epilog=(
            f"""
This subcommand allows checking if all facts are up to date.

Examples:

  $ clan facts check [MACHINE]
  Will check facts for the specified machine.


For more detailed information, visit: {help_hyperlink("secrets", "https://docs.clan.lol/getting-started/secrets")}
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_check_parser(check_parser)

    list_parser = subparser.add_parser(
        "list",
        help="list all facts",
        epilog=(
            f"""
This subcommand allows listing all public facts for a specific machine.

The resulting list will be a json string with the name of the fact as its key
and the fact itself as it's value.

This is how an example output might look like:
```
\u007b
"[FACT_NAME]": "[FACT]"
\u007d
```

Examples:

  $ clan facts list [MACHINE]
  Will list facts for the specified machine.

   
For more detailed information, visit: {help_hyperlink("secrets", "https://docs.clan.lol/getting-started/secrets")}
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_list_parser(list_parser)

    parser_generate = subparser.add_parser(
        "generate",
        help="generate public and secret facts for machines",
        epilog=(
            f"""
This subcommand allows control of the generation of facts.
Often this function will be invoked automatically on deploying machines,
but there are situations the user may want to have more granular control,
especially for the regeneration of certain services.

A service is an included clan-module that implements facts generation functionality.
For example the zerotier module will generate private and public facts.
In this case the public fact will be the resulting zerotier-ip of the machine.
The secret fact will be the zerotier-identity-secret, which is used by zerotier
to prove the machine has control of the zerotier-ip.


Examples:

  $ clan facts generate
  Will generate facts for all machines.
   
  $ clan facts generate [MACHINE]
  Will generate facts for the specified machine.

  $ clan facts generate [MACHINE] --service [SERVICE]
  Will generate facts for the specified machine for the specified service.

  $ clan facts generate --service [SERVICE] --regenerate
  Will regenerate facts, if they are already generated for a specific service.
  This is especially useful for resetting certain passwords while leaving the rest
  of the facts for a machine in place.

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

  $ clan facts upload [MACHINE]
  Will upload secrets to a specific machine.
   
For more detailed information, visit: {help_hyperlink("secrets", "https://docs.clan.lol/getting-started/secrets")}
        """
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    register_upload_parser(parser_upload)
