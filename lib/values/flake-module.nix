{ self, inputs, ... }:
let
  inputOverrides = builtins.concatStringsSep " " (
    builtins.map (input: " --override-input ${input} ${inputs.${input}}") (builtins.attrNames inputs)
  );
in
{
  perSystem =
    {
      pkgs,
      system,
      lib,
      ...
    }:
    let
      tests = import ./test.nix { inherit lib; };
    in
    {
      legacyPackages.evalTests-values = tests;
      checks = {
        lib-values-eval = pkgs.runCommand "tests" { nativeBuildInputs = [ pkgs.nix-unit ]; } ''
          export HOME="$(realpath .)"

          nix-unit --eval-store "$HOME" \
            --extra-experimental-features flakes \
            ${inputOverrides} \
            --flake ${
              self.filter {
                include = [
                  "flakeModules"
                  "lib/default.nix"
                  "lib/flake-module.nix"
                  "lib/values"
                ];
              }
            }#legacyPackages.${system}.evalTests-values

          touch $out
        '';
      };
    };
}
