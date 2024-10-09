{ self, inputs, ... }:
let
  inputOverrides = builtins.concatStringsSep " " (
    builtins.map (input: " --override-input ${input} ${inputs.${input}}") (builtins.attrNames inputs)
  );
in
{
  flake.inventory = import ./example.nix { inherit self; };

  perSystem =
    {
      pkgs,
      lib,
      config,
      system,
      self',
      ...
    }:
    {
      devShells.inventory-schema = pkgs.mkShell {
        inputsFrom = with config.checks; [
          lib-inventory-examples-cue
          lib-inventory-eval
          self'.devShells.default
        ];
      };

      legacyPackages.schemas = (
        import ./schemas {
          inherit
            pkgs
            self
            lib
            self'
            ;
        }
      );

      # Run: nix-unit --extra-experimental-features flakes --flake .#legacyPackages.x86_64-linux.evalTests
      legacyPackages.evalTests-inventory = import ./tests {
        inherit lib;
        clan-core = self;
      };

      checks = {
        lib-inventory-eval = pkgs.runCommand "tests" { nativeBuildInputs = [ pkgs.nix-unit ]; } ''
          export HOME="$(realpath .)"

          nix-unit --eval-store "$HOME" \
            --extra-experimental-features flakes \
            ${inputOverrides} \
            --flake ${self}#legacyPackages.${system}.evalTests-inventory

          touch $out
        '';
      };
    };
}
