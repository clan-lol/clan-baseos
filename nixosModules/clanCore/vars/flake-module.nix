{
  self,
  inputs,
  lib,
  ...
}:
let
  inputOverrides = builtins.concatStringsSep " " (
    builtins.map (input: " --override-input ${input} ${inputs.${input}}") (builtins.attrNames inputs)
  );
in
{
  perSystem =
    { system, pkgs, ... }:
    {
      legacyPackages.evalTests-module-clan-vars = import ./eval-tests {
        inherit lib;
        clan-core = self;
        pkgs = inputs.nixpkgs.legacyPackages.${system};
      };
      checks.module-clan-vars-eval = pkgs.runCommand "tests" { nativeBuildInputs = [ pkgs.nix-unit ]; } ''
        export HOME="$(realpath .)"

        nix-unit --eval-store "$HOME" \
          --extra-experimental-features flakes \
          ${inputOverrides} \
          --flake ${
            self.filter {
              include = [
                "flakeModules"
                "nixosModules"
              ];
            }
          }#legacyPackages.${system}.evalTests-module-clan-vars

        touch $out
      '';
    };
}
