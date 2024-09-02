# !/usr/bin/env python3
import argparse
import datetime

from clan_cli.clan.inspect import inspect_flake
from clan_cli.clan_uri import ClanURI
from clan_cli.errors import ClanCmdError
from clan_cli.locked_open import write_history_file
from clan_cli.nix import nix_metadata

from .add import HistoryEntry, list_history


def update_history() -> list[HistoryEntry]:
    logs = list_history()

    for entry in logs:
        try:
            meta = nix_metadata(str(entry.flake.flake_url))
        except ClanCmdError as e:
            print(f"Failed to update {entry.flake.flake_url}: {e}")
            continue

        new_hash = meta["locked"]["narHash"]
        if new_hash != entry.flake.nar_hash:
            print(
                f"Updating {entry.flake.flake_url} from {entry.flake.nar_hash} to {new_hash}"
            )
            uri = ClanURI.from_str(
                url=str(entry.flake.flake_url),
                machine_name=entry.flake.flake_attr,
            )
            flake = inspect_flake(uri.get_url(), uri.machine_name)
            flake.flake_url = flake.flake_url
            entry = HistoryEntry(
                flake=flake, last_used=datetime.datetime.now().isoformat()
            )

    write_history_file(logs)
    return logs


def add_update_command(args: argparse.Namespace) -> None:
    update_history()


# takes a (sub)parser and configures it
def register_update_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=add_update_command)
