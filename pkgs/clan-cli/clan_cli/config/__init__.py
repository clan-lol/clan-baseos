# !/usr/bin/env python3
import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, get_origin

from clan_cli.cmd import run
from clan_cli.dirs import machine_settings_file
from clan_cli.errors import ClanError
from clan_cli.git import commit_file
from clan_cli.nix import nix_eval

script_dir = Path(__file__).parent

log = logging.getLogger(__name__)


# nixos option type description to python type
def map_type(nix_type: str) -> Any:
    if nix_type == "boolean":
        return bool
    if nix_type in [
        "integer",
        "signed integer",
        "16 bit unsigned integer; between 0 and 65535 (both inclusive)",
    ]:
        return int
    if nix_type.startswith("string"):
        return str
    if nix_type.startswith("null or "):
        subtype = nix_type.removeprefix("null or ")
        return map_type(subtype) | None
    if nix_type.startswith("attribute set of"):
        subtype = nix_type.removeprefix("attribute set of ")
        return dict[str, map_type(subtype)]  # type: ignore
    if nix_type.startswith("list of"):
        subtype = nix_type.removeprefix("list of ")
        return list[map_type(subtype)]  # type: ignore
    msg = f"Unknown type {nix_type}"
    raise ClanError(msg)


# merge two dicts recursively
def merge(a: dict, b: dict, path: list[str] | None = None) -> dict:
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], [*path, str(key)])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key].extend(b[key])
            elif a[key] != b[key]:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


# A container inheriting from list, but overriding __contains__ to return True
# for all values.
# This is used to allow any value for the "choices" field of argparse
class AllContainer(list):
    def __contains__(self, item: Any) -> bool:
        return True


# value is always a list, as the arg parser cannot know the type upfront
# and therefore always allows multiple arguments.
def cast(value: Any, input_type: Any, opt_description: str) -> Any:
    try:
        # handle bools
        if isinstance(input_type, bool):
            if value[0] in ["true", "True", "yes", "y", "1"]:
                return True
            if value[0] in ["false", "False", "no", "n", "0"]:
                return False
            msg = f"Invalid value {value} for boolean"
            raise ClanError(msg)
        # handle lists
        if get_origin(input_type) is list:
            subtype = input_type.__args__[0]
            return [cast([x], subtype, opt_description) for x in value]
        # handle dicts
        if get_origin(input_type) is dict:
            if not isinstance(value, dict):
                msg = f"Cannot set {opt_description} directly. Specify a suboption like {opt_description}.<name>"
                raise ClanError(msg)
            subtype = input_type.__args__[1]
            return {k: cast(v, subtype, opt_description) for k, v in value.items()}
        if str(input_type) == "str | None":
            if value[0] in ["null", "None"]:
                return None
            return value[0]
        if len(value) > 1:
            msg = f"Too many values for {opt_description}"
            raise ClanError(msg)
        return input_type(value[0])
    except ValueError as e:
        msg = f"Invalid type for option {opt_description} (expected {input_type.__name__})"
        raise ClanError(msg) from e


def options_for_machine(
    flake_dir: Path, machine_name: str, show_trace: bool = False
) -> dict:
    clan_dir = flake_dir
    flags = []
    if show_trace:
        flags.append("--show-trace")
    flags.append(
        f"{clan_dir}#nixosConfigurations.{machine_name}.config.clan.core.optionsNix"
    )
    cmd = nix_eval(flags=flags)
    proc = run(
        cmd,
        error_msg=f"Failed to read options for machine {machine_name}",
    )

    return json.loads(proc.stdout)


def read_machine_option_value(
    flake_dir: Path, machine_name: str, option: str, show_trace: bool = False
) -> str:
    clan_dir = flake_dir
    # use nix eval to read from .#nixosConfigurations.default.config.{option}
    # this will give us the evaluated config with the options attribute
    cmd = nix_eval(
        flags=[
            "--show-trace",
            f"{clan_dir}#nixosConfigurations.{machine_name}.config.{option}",
        ],
    )
    proc = run(cmd, error_msg=f"Failed to read option {option}")

    value = json.loads(proc.stdout)
    # print the value so that the output can be copied and fed as an input.
    # for example a list should be displayed as space separated values surrounded by quotes.
    if isinstance(value, list):
        out = " ".join([json.dumps(x) for x in value])
    elif isinstance(value, dict):
        out = json.dumps(value, indent=2)
    else:
        out = json.dumps(value, indent=2)
    return out


def get_option(args: argparse.Namespace) -> None:
    print(
        read_machine_option_value(
            args.flake, args.machine, args.option, args.show_trace
        )
    )


# Currently writing is disabled
def get_or_set_option(args: argparse.Namespace) -> None:
    if args.value == []:
        print(
            read_machine_option_value(
                args.flake, args.machine, args.option, args.show_trace
            )
        )
    else:
        # load options
        if args.options_file is None:
            options = options_for_machine(
                args.flake, machine_name=args.machine, show_trace=args.show_trace
            )
        else:
            with open(args.options_file) as f:
                options = json.load(f)
        # compute settings json file location
        if args.settings_file is None:
            settings_file = machine_settings_file(args.flake.path, args.machine)
        else:
            settings_file = args.settings_file
        # set the option with the given value
        set_option(
            flake_dir=args.flake.path,
            option=args.option,
            value=args.value,
            options=options,
            settings_file=settings_file,
            option_description=args.option,
            show_trace=args.show_trace,
        )
        if not args.quiet:
            new_value = read_machine_option_value(args.flake, args.machine, args.option)
            print(f"New Value for {args.option}:")
            print(new_value)


def find_option(
    option: str, value: Any, options: dict, option_description: str | None = None
) -> tuple[str, Any]:
    """
    The option path specified by the user doesn't have to match exactly to an
    entry in the options.json file. Examples

    Example 1:
        $ clan config services.openssh.settings.SomeSetting 42
    This is a freeform option that does not appear in the options.json
    The actual option is `services.openssh.settings`
    And the value must be wrapped: {"SomeSettings": 42}

    Example 2:
        $ clan config users.users.my-user.name my-name
    The actual option is `users.users.<name>.name`
    """

    # option description is used for error messages
    if option_description is None:
        option_description = option

    option_path = option.split(".")

    # fuzzy search the option paths, so when
    #   specified option path: "foo.bar.baz.bum"
    #   available option path: "foo.<name>.baz.<name>"
    # we can still find the option
    first = option_path[0]
    regex = rf"({first}|<name>)"
    for elem in option_path[1:]:
        regex += rf"\.({elem}|<name>)"
    for opt in options:
        if re.match(regex, opt):
            return opt, value

    # if the regex search did not find the option, start stripping the last
    # element of the option path and find matching parent option
    # (see examples above for why this is needed)
    if len(option_path) == 1:
        msg = f"Option {option_description} not found"
        raise ClanError(msg)
    option_path_parent = option_path[:-1]
    attr_prefix = option_path[-1]
    return find_option(
        option=".".join(option_path_parent),
        value={attr_prefix: value},
        options=options,
        option_description=option_description,
    )


def set_option(
    flake_dir: Path,
    option: str,
    value: Any,
    options: dict,
    settings_file: Path,
    option_description: str = "",
    show_trace: bool = False,
) -> None:
    option_path_orig = option.split(".")

    # returns for example:
    #   option: "users.users.<name>.name"
    #   value: "my-name"
    option, value = find_option(
        option=option,
        value=value,
        options=options,
        option_description=option_description,
    )
    option_path = option.split(".")

    option_path_store = option_path_orig[: len(option_path)]

    target_type = map_type(options[option]["type"])
    casted = cast(value, target_type, option)

    # construct a nested dict from the option path and set the value
    result: dict[str, Any] = {}
    current = result
    for part in option_path_store[:-1]:
        current[part] = {}
        current = current[part]
    current[option_path_store[-1]] = value

    current[option_path_store[-1]] = casted

    # check if there is an existing config file
    if os.path.exists(settings_file):
        with open(settings_file) as f:
            current_config = json.load(f)
    else:
        current_config = {}

    # merge and save the new config file
    new_config = merge(current_config, result)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_file, "w") as f:
        json.dump(new_config, f, indent=2)
        print(file=f)  # add newline at the end of the file to make git happy

    if settings_file.resolve().is_relative_to(flake_dir):
        commit_file(
            settings_file,
            repo_dir=flake_dir,
            commit_message=f"Set option {option_description}",
        )
