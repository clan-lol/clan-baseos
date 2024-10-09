{
  lib,
  clan-core,
  nixpkgs,
  ...
}:
let
  eval = import ./eval-clan-modules {
    inherit clan-core lib;
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
  };
in
{
  inherit (eval) evalClanModules evalClanModulesWithRoles;
  buildClan = import ./build-clan { inherit lib nixpkgs clan-core; };
  facts = import ./facts.nix { inherit lib; };
  inventory = import ./inventory { inherit lib clan-core; };
  jsonschema = import ./jsonschema { inherit lib; };
  modules = import ./description.nix { inherit clan-core lib; };
}
