import json
from json.decoder import JSONDecodeError
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import AnyUrl

from clan_cli import flakes
from clan_cli.webui.api_inputs import (
    FlakeCreateInput,
)
from clan_cli.webui.api_outputs import (
    FlakeAction,
    FlakeAttrResponse,
    FlakeCreateResponse,
    FlakeResponse,
)

from ...async_cmd import run
from ...flakes import add, create
from ...nix import nix_command, nix_flake_show
from ..tags import Tags

router = APIRouter()


# TODO: Check for directory traversal
async def get_attrs(url: AnyUrl | Path) -> list[str]:
    cmd = nix_flake_show(url)
    out = await run(cmd)

    data: dict[str, dict] = {}
    try:
        data = json.loads(out.stdout)
    except JSONDecodeError:
        raise HTTPException(status_code=422, detail="Could not load flake.")

    nixos_configs = data.get("nixosConfigurations", {})
    flake_attrs = list(nixos_configs.keys())

    if not flake_attrs:
        raise HTTPException(
            status_code=422, detail="No entry or no attribute: nixosConfigurations"
        )
    return flake_attrs


@router.post("/api/flake/history", tags=[Tags.flake])
async def flake_history_append(flake_dir: Path) -> None:
    await add.add_flake(flake_dir)


@router.get("/api/flake/history", tags=[Tags.flake])
async def flake_history_list() -> list[Path]:
    return flakes.history.list_history()


# TODO: Check for directory traversal
@router.get("/api/flake/attrs", tags=[Tags.flake])
async def inspect_flake_attrs(url: AnyUrl | Path) -> FlakeAttrResponse:
    return FlakeAttrResponse(flake_attrs=await get_attrs(url))


# TODO: Check for directory traversal
@router.get("/api/flake/inspect", tags=[Tags.flake])
async def inspect_flake(
    url: AnyUrl | Path,
) -> FlakeResponse:
    actions = []
    # Extract the flake from the given URL
    # We do this by running 'nix flake prefetch {url} --json'
    cmd = nix_command(["flake", "prefetch", str(url), "--json", "--refresh"])
    out = await run(cmd)
    data: dict[str, str] = json.loads(out.stdout)

    if data.get("storePath") is None:
        raise HTTPException(status_code=500, detail="Could not load flake")

    content: str
    with open(Path(data.get("storePath", "")) / Path("flake.nix")) as f:
        content = f.read()

    # TODO: Figure out some measure when it is insecure to inspect or create a VM
    actions.append(FlakeAction(id="vms/inspect", uri="api/vms/inspect"))
    actions.append(FlakeAction(id="vms/create", uri="api/vms/create"))

    return FlakeResponse(content=content, actions=actions)


@router.post(
    "/api/flake/create", tags=[Tags.flake], status_code=status.HTTP_201_CREATED
)
async def create_flake(
    flake_dir: Path, args: Annotated[FlakeCreateInput, Body()]
) -> FlakeCreateResponse:
    if flake_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Flake already exists",
        )

    cmd_out = await create.create_flake(flake_dir, args.url)
    return FlakeCreateResponse(cmd_out=cmd_out)
