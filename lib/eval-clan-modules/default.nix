{
  nixpkgs,
  clan-core,
  lib,
}:
let
  inherit (import nixpkgs { system = "x86_64-linux"; }) pkgs;

  inherit (clan-core) clanModules;

  baseModule = {
    imports = (import (pkgs.path + "/nixos/modules/module-list.nix")) ++ [
      {
        nixpkgs.hostPlatform = "x86_64-linux";
        clan.core.name = "dummy";
      }
    ];
  };

  # This function takes a list of module names and evaluates them
  # evalClanModules :: [ String ] -> { config, options, ... }
  evalClanModules =
    modulenames:
    let
      evaled = lib.evalModules {
        modules = [
          baseModule
          clan-core.nixosModules.clanCore
        ] ++ (map (name: clanModules.${name}) modulenames);
      };
    in
    evaled;
in
evalClanModules
