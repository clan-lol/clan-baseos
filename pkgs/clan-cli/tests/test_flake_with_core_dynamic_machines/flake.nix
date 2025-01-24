{
  # Use this path to our repo root e.g. for UI test
  # inputs.clan-core.url = "../../../../.";

  # this placeholder is replaced by the path to nixpkgs
  inputs.clan-core.url = "__CLAN_CORE__";

  outputs =
    { self, clan-core }:
    let
      clan = clan-core.lib.buildClan {
        inherit self;
        meta.name = "test_flake_with_core_dynamic_machines";
        machines =
          let
            machineModules = builtins.readDir (self + "/machines");
          in
          builtins.mapAttrs (name: _type: import (self + "/machines/${name}")) machineModules;
      };
    in
    {
      inherit (clan) nixosConfigurations clanInternals;
    };
}
