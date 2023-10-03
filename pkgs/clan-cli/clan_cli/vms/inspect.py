import argparse
import asyncio
import json

from pydantic import BaseModel

from ..async_cmd import run
from ..dirs import get_clan_flake_toplevel
from ..nix import nix_eval


class VmConfig(BaseModel):
    flake_url: str
    flake_attr: str

    cores: int
    memory_size: int
    graphics: bool


async def inspect_vm(flake_url: str, flake_attr: str) -> VmConfig:
    cmd = nix_eval(
        [
            f"{flake_url}#nixosConfigurations.{json.dumps(flake_attr)}.config.system.clan.vm.config"
        ]
    )
    stdout = await run(cmd)
    data = json.loads(stdout)
    return VmConfig(flake_url=flake_url, flake_attr=flake_attr, **data)


def inspect_command(args: argparse.Namespace) -> None:
    clan_dir = get_clan_flake_toplevel().as_posix()
    res = asyncio.run(inspect_vm(flake_url=clan_dir, flake_attr=args.machine))
    print("Cores:", res.cores)
    print("Memory size:", res.memory_size)
    print("Graphics:", res.graphics)


def register_inspect_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("machine", type=str)
    parser.set_defaults(func=inspect_command)
