{
  inputs,
  self,
  lib,
  ...
}:
{
  perSystem =
    {
      self',
      pkgs,
      ...
    }:
    let
      flakeLock = lib.importJSON (self + /flake.lock);
      flakeInputs = builtins.removeAttrs inputs [ "self" ];
      flakeLockVendoredDeps = flakeLock // {
        nodes =
          flakeLock.nodes
          // (lib.flip lib.mapAttrs flakeInputs (
            name: _:
            flakeLock.nodes.${name}
            // {
              locked = {
                inherit (flakeLock.nodes.${name}.locked) narHash;
                lastModified =
                  # lol, nixpkgs has a different timestamp on the fs???
                  if name == "nixpkgs" then 0 else 1;
                path = "${inputs.${name}}";
                type = "path";
              };
            }
          ));
      };
      flakeLockFile = builtins.toFile "clan-core-flake.lock" (builtins.toJSON flakeLockVendoredDeps);
      clanCoreWithVendoredDeps = pkgs.runCommand "clan-core-with-vendored-deps" { } ''
        cp -r ${self} $out
        chmod +w -R $out
        cp ${flakeLockFile} $out/flake.lock
      '';
    in
    {
      devShells.clan-cli = pkgs.callPackage ./shell.nix {
        inherit (self'.packages) clan-cli clan-cli-full;
        inherit self';
      };
      packages = {
        clan-cli = pkgs.python3.pkgs.callPackage ./default.nix {
          inherit (inputs) nixpkgs;
          inherit (self'.packages) classgen;
          inherit (self'.legacyPackages.schemas) inventory-schema-abstract;
          clan-core-path = clanCoreWithVendoredDeps;
          includedRuntimeDeps = [
            "age"
            "git"
          ];
        };
        clan-cli-full = pkgs.python3.pkgs.callPackage ./default.nix {
          inherit (inputs) nixpkgs;
          inherit (self'.packages) classgen;
          inherit (self'.legacyPackages.schemas) inventory-schema-abstract;
          clan-core-path = clanCoreWithVendoredDeps;
          includedRuntimeDeps = lib.importJSON ./clan_cli/nix/allowed-programs.json;
        };
        clan-cli-docs = pkgs.stdenv.mkDerivation {
          name = "clan-cli-docs";
          src = ./.;

          buildInputs = [
            # TODO: see postFixup clan-cli/default.nix:L188
            pkgs.python3
            self'.packages.clan-cli.propagatedBuildInputs
          ];

          installPhase = ''
            ${self'.packages.classgen}/bin/classgen ${self'.legacyPackages.schemas.inventory-schema-abstract}/schema.json ./clan_cli/inventory/classes.py --stop-at "Service"

            python docs.py reference
            mkdir -p $out
            cp -r out/* $out
            ls -lah $out
          '';
        };
        clan-ts-api = pkgs.stdenv.mkDerivation {
          name = "clan-ts-api";
          src = ./.;

          buildInputs = [
            pkgs.python3
            pkgs.json2ts
          ];

          installPhase = ''
            ${self'.packages.classgen}/bin/classgen ${self'.legacyPackages.schemas.inventory-schema-abstract}/schema.json ./clan_cli/inventory/classes.py --stop-at "Service"
            mkdir -p $out
            # Retrieve python API Typescript types
            python api.py > $out/API.json
            json2ts --input $out/API.json > $out/API.ts

            # Retrieve python API Typescript types
            json2ts --input ${self'.legacyPackages.schemas.inventory}/schema.json > $out/Inventory.ts
            cp ${self'.legacyPackages.schemas.inventory}/* $out
          '';
        };

        default = self'.packages.clan-cli;
      };

      checks = self'.packages.clan-cli.tests // {
        inventory-classes-up-to-date = pkgs.stdenv.mkDerivation {
          name = "inventory-classes-up-to-date";
          src = ./clan_cli/inventory;

          env = {
            classFile = "classes.py";
          };
          installPhase = ''
            ${self'.packages.classgen}/bin/classgen ${self'.legacyPackages.schemas.inventory-schema-abstract}/schema.json b_classes.py --stop-at "Service"
            file1=$classFile
            file2=b_classes.py

            echo "Comparing $file1 and $file2"
            if cmp -s "$file1" "$file2"; then
                echo "Files are identical"
                echo "Classes file is up to date"
            else
                echo "Classes file is out of date or has been modified"
                echo "run 'direnv reload' in the pkgs/clan-cli directory to refresh the classes file"
                echo "--------------------------------\n"
                diff "$file1" "$file2"
                echo "--------------------------------\n\n"
                exit 1
            fi

            touch $out
          '';
        };
      };
    };
}
