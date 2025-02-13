test:
{ pkgs, self, ... }:
let
  inherit (pkgs) lib;
  nixos-lib = import (pkgs.path + "/nixos/lib") { };
in
(nixos-lib.runTest {
  hostPkgs = pkgs;
  # speed-up evaluation
  defaults = (
    { config, ... }:
    {
      imports = [
        ./minify.nix
      ];
      documentation.enable = lib.mkDefault false;
      nix.settings.min-free = 0;
      system.stateVersion = config.system.nixos.release;
    }
  );

  _module.args = { inherit self; };
  # to accept external dependencies such as disko
  node.specialArgs.self = self;
  imports = [ test ];
}).config.result
