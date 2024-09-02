import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from clan_cli.api import API
from clan_cli.cmd import run
from clan_cli.dirs import nixpkgs_source
from clan_cli.errors import ClanError, ClanHttpError
from clan_cli.nix import nix_eval


# TODO: When moving the api to `clan-app`, the whole config module should be
# ported to the `clan-app`, because it is not used by the cli at all.
@API.register
def machine_schema(
    flake_dir: Path,
    config: dict[str, Any],
    clan_imports: list[str] | None = None,
    option_path: list[str] | None = None,
) -> dict[str, Any]:
    if option_path is None:
        option_path = ["clan"]
    # use nix eval to lib.evalModules .#nixosConfigurations.<machine_name>.options.clan
    with NamedTemporaryFile(mode="w", dir=flake_dir) as clan_machine_settings_file:
        env = os.environ.copy()
        if clan_imports is not None:
            config["clanImports"] = clan_imports
        # dump config to file
        json.dump(config, clan_machine_settings_file, indent=2)
        clan_machine_settings_file.seek(0)
        env["CLAN_MACHINE_SETTINGS_FILE"] = clan_machine_settings_file.name
        # ensure that the requested clanImports exist
        proc = run(
            nix_eval(
                flags=[
                    "--impure",
                    "--show-trace",
                    "--expr",
                    f"""
                    let
                        b = builtins;
                        system = b.currentSystem;
                        flake = b.getFlake (toString {flake_dir});
                        clan-core = flake.inputs.clan-core;
                        config = b.fromJSON (b.readFile (b.getEnv "CLAN_MACHINE_SETTINGS_FILE"));
                        modules_not_found =
                            b.filter
                            (modName: ! clan-core.clanModules ? ${{modName}})
                            config.clanImports or [];
                    in
                        modules_not_found
                    """,
                ]
            ),
            cwd=flake_dir,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            raise ClanHttpError(
                status_code=400,
                msg=f"Failed to check clanImports for existence:\n{proc.stderr}",
            )
        modules_not_found = json.loads(proc.stdout)
        if len(modules_not_found) > 0:
            raise ClanHttpError(
                msg="Some requested clan modules could not be found", status_code=400
            )

        # get the schema
        proc = run(
            nix_eval(
                flags=[
                    "--impure",
                    "--show-trace",
                    "--expr",
                    f"""
                    let
                        system = builtins.currentSystem;
                        flake = builtins.getFlake (toString {flake_dir});
                        clan-core = flake.inputs.clan-core;
                        nixpkgsSrc = flake.inputs.nixpkgs or {nixpkgs_source()};
                        lib = import (nixpkgsSrc + /lib);
                        pkgs = import nixpkgsSrc {{ inherit system; }};
                        config = lib.importJSON (builtins.getEnv "CLAN_MACHINE_SETTINGS_FILE");
                        fakeMachine = pkgs.nixos {{
                            imports =
                                [
                                    clan-core.nixosModules.clanCore
                                    # potentially the config might affect submodule options,
                                    # therefore we need to import it
                                    config
                                    {{ clan.core.name = "fakeClan"; }}
                                ]
                                # add all clan modules specified via clanImports
                                ++ (map (name: clan-core.clanModules.${{name}}) config.clanImports or []);
                        }};
                        options = fakeMachine.options{"." + ".".join(option_path) if option_path else ""};
                        jsonschemaLib = import {Path(__file__).parent / "jsonschema"} {{ inherit lib; }} {{}};
                        jsonschema = jsonschemaLib.parseOptions options {{}};
                    in
                        jsonschema
                    """,
                ],
            ),
            check=False,
            cwd=flake_dir,
            env=env,
        )
    if proc.returncode != 0:
        msg = f"Failed to read schema:\n{proc.stderr}"
        raise ClanError(msg)
    return json.loads(proc.stdout)
