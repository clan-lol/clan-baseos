import argparse
import logging

from clan_cli.templates import list_templates

log = logging.getLogger(__name__)


def list_command(args: argparse.Namespace) -> None:
    template_list = list_templates("clan", args.flake)

    print("Available local templates:")
    for name, template in template_list.self.items():
        print(f"  {name}: {template['description']}")

    print("Available templates from inputs:")
    for input_name, input_templates in template_list.inputs.items():
        print(f"  {input_name}:")
        for name, template in input_templates.items():
            print(f"    {name}: {template['description']}")


def register_list_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=list_command)
