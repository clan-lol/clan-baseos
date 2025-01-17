{
  lib,
  inputs,
  self,
  ...
}:
let
  inherit (lib)
    filter
    pathExists
    ;
in
{
  imports = filter pathExists [
    ./jsonschema/flake-module.nix
    ./inventory/flake-module.nix
    ./build-clan/flake-module.nix
    ./values/flake-module.nix
  ];
  flake.lib = import ./default.nix {
    inherit lib inputs;
    inherit (inputs) nixpkgs;
    clan-core = self;
  };
}
