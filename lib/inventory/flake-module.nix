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
    let
      getSchema = import ./interface-to-schema.nix { inherit lib self; };

      # The schema for the inventory, without default values, from the module system.
      # This is better suited for human reading and for generating code.
      bareSchema = getSchema { includeDefaults = false; };
      # The schema for the inventory with default values, from the module system.
      # This is better suited for validation, since default values are included.
      fullSchema = getSchema { };
    in
    {
      legacyPackages.inventory = {
        inherit fullSchema;
        inherit bareSchema;
      };

      devShells.inventory-schema = pkgs.mkShell {
        inputsFrom = with config.checks; [
          lib-inventory-examples-cue
          lib-inventory-eval
          self'.devShells.default
        ];
      };

      # Inventory schema with concrete module implementations
      packages.inventory-api-docs = pkgs.stdenv.mkDerivation {
        name = "inventory-schema";
        buildInputs = [ ];
        src = ./.;
        buildPhase = ''
          cat <<EOF > "$out"
          # Inventory API

          *Inventory* is an abstract service layer for consistently configuring distributed services across machine boundaries.

          The following is a specification of the inventory in [cuelang](https://cuelang.org/) format.

          \`\`\`cue
          EOF

          cat ${self'.packages.inventory-schema-pretty}/schema.cue >> $out

          cat <<EOF >> $out
          \`\`\`
          EOF
        '';
      };

      packages.inventory-schema = pkgs.stdenv.mkDerivation {
        name = "inventory-schema";
        buildInputs = [ pkgs.cue ];
        src = ./.;
        buildPhase = ''
          export SCHEMA=${builtins.toFile "inventory-schema.json" (builtins.toJSON fullSchema.schemaWithModules)}
          cp $SCHEMA schema.json
          cue import -f -p compose -l '#Root:' schema.json
          mkdir $out
          cp schema.cue $out
          cp schema.json $out
        '';
      };
      packages.inventory-schema-abstract = pkgs.stdenv.mkDerivation {
        name = "inventory-schema";
        buildInputs = [ pkgs.cue ];
        src = ./.;
        buildPhase = ''
          export SCHEMA=${builtins.toFile "inventory-schema.json" (builtins.toJSON bareSchema.abstractSchema)}
          cp $SCHEMA schema.json
          cue import -f -p compose -l '#Root:' schema.json
          mkdir $out
          cp schema.cue $out
          cp schema.json $out
        '';
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

      packages.inventory-schema-pretty = pkgs.stdenv.mkDerivation {
        name = "inventory-schema-pretty";
        buildInputs = [ pkgs.cue ];
        src = ./.;
        buildPhase = ''
          export SCHEMA=${builtins.toFile "inventory-schema.json" (builtins.toJSON bareSchema.schemaWithModules)}
          cp $SCHEMA schema.json
          cue import -f -p compose -l '#Root:' schema.json
          mkdir $out
          cp schema.cue $out
          cp schema.json $out
        '';
      };

      # Run: nix-unit --extra-experimental-features flakes --flake .#legacyPackages.x86_64-linux.evalTests
      legacyPackages.evalTests-inventory = import ./tests {
        inherit lib;
        clan-core = self;
      };

      checks = {
        lib-inventory-examples-cue = pkgs.stdenv.mkDerivation {
          name = "inventory-schema-checks";
          src = ./.;
          buildInputs = [ pkgs.cue ];
          buildPhase = ''
            echo "Running inventory tests..."
            # Cue is easier to run in the same directory as the schema
            cp ${self'.packages.inventory-schema}/schema.cue root.cue

            ls -la .

            echo "Validate test/*.json against inventory-schema..."
            cat root.cue

            test_dir="./examples"
            for file in "$test_dir"/*; do
              # Check if the item is a file
              if [ -f "$file" ]; then
                # Print the filename
                echo "Running test on: $file"

                # Run the cue vet command
                cue vet "$file" root.cue -d "#Root"
              fi
            done

            touch $out
          '';
        };
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
