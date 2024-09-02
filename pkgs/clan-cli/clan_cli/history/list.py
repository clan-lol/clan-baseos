# !/usr/bin/env python3
import argparse
from datetime import datetime

from .add import HistoryEntry, list_history


def list_history_command(args: argparse.Namespace) -> None:
    res: dict[str, list[HistoryEntry]] = {}
    for history_entry in list_history():
        url = str(history_entry.flake.flake_url)
        if res.get(url) is None:
            res[url] = []
        res[url].append(history_entry)

    for flake_url, entries in res.items():
        print(flake_url)
        for entry in entries:
            d = datetime.fromisoformat(entry.last_used)
            last_used = d.strftime("%d/%m/%Y %H:%M:%S")
            print(f"  {entry.flake.flake_attr} ({last_used})")


# takes a (sub)parser and configures it
def register_list_parser(parser: argparse.ArgumentParser) -> None:
    parser.set_defaults(func=list_history_command)
