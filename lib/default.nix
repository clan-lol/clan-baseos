{
  lib,
  clan-core,
  nixpkgs,
  ...
}:
let
  evalClan = import ./eval-clan-modules {
    inherit clan-core lib;
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
  };
in
{
  inherit (evalClan) evalClanModules evalClanModulesWithRoles;
  buildClan = import ./build-clan { inherit lib nixpkgs clan-core; };
  facts = import ./facts.nix { inherit lib; };
  inventory = import ./inventory { inherit lib clan-core; };
  values = import ./values { inherit lib; };
  jsonschema = import ./jsonschema { inherit lib; };
  modules = import ./frontmatter {
    inherit lib;
    self = clan-core;
  };
}
