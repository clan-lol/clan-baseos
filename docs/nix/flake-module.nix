{ inputs, self, ... }:
{
  perSystem =
    {
      config,
      self',
      pkgs,
      ...
    }:
    let
      buildClanOptions = self'.legacyPackages.clan-internals-docs;
      # Simply evaluated options (JSON)
      # { clanCore = «derivation JSON»; clanModules = { ${name} = «derivation JSON» }; }
      jsonDocs = import ./get-module-docs.nix {
        inherit (inputs) nixpkgs;
        inherit pkgs;
        inherit (self.nixosModules) clanCore;
        inherit (self) clanModules;
      };

      clanModulesFileInfo = pkgs.writeText "info.json" (builtins.toJSON jsonDocs.clanModules);
      # clanModulesReadmes = pkgs.writeText "info.json" (builtins.toJSON jsonDocs.clanModulesReadmes);
      # clanModulesMeta = pkgs.writeText "info.json" (builtins.toJSON jsonDocs.clanModulesMeta);

      # Simply evaluated options (JSON)
      renderOptions =
        pkgs.runCommand "render-options"
          {
            # TODO: ruff does not splice properly in nativeBuildInputs
            depsBuildBuild = [ pkgs.ruff ];
            nativeBuildInputs = [
              pkgs.python3
              pkgs.mypy
              self'.packages.clan-cli
            ];
          }
          ''
            install -D -m755 ${./render_options}/__init__.py $out/bin/render-options
            patchShebangs --build $out/bin/render-options

            ruff format --check --diff $out/bin/render-options
            ruff check --line-length 88 $out/bin/render-options
            mypy --strict $out/bin/render-options
          '';

      asciinema-player-js = pkgs.fetchurl {
        url = "https://github.com/asciinema/asciinema-player/releases/download/v3.7.0/asciinema-player.min.js";
        sha256 = "sha256-Ymco/+FinDr5YOrV72ehclpp4amrczjo5EU3jfr/zxs=";
      };
      asciinema-player-css = pkgs.fetchurl {
        url = "https://github.com/asciinema/asciinema-player/releases/download/v3.7.0/asciinema-player.css";
        sha256 = "sha256-GZMeZFFGvP5GMqqh516mjJKfQaiJ6bL38bSYOXkaohc=";
      };

      module-docs =
        pkgs.runCommand "rendered"
          {
            buildInputs = [
              pkgs.python3
              self'.packages.clan-cli
              # TODO: see postFixup clan-cli/default.nix:L188
              self'.packages.clan-cli.propagatedBuildInputs
            ];
          }
          ''
            export CLAN_CORE_PATH=${self}
            export CLAN_CORE_DOCS=${jsonDocs.clanCore}/share/doc/nixos/options.json
            # A file that contains the links to all clanModule docs
            export CLAN_MODULES=${clanModulesFileInfo}

            # buildClan options
            export BUILD_CLAN_PATH=${buildClanOptions}/share/doc/nixos/options.json

            mkdir $out

            # The python script will place mkDocs files in the output directory
            exec python3 ${renderOptions}/bin/render-options
          '';
    in
    {
      devShells.docs = pkgs.callPackage ./shell.nix {
        inherit (self'.packages) docs clan-cli-docs inventory-api-docs;
        inherit
          asciinema-player-js
          asciinema-player-css
          module-docs
          self'
          ;
      };
      packages = {
        docs = pkgs.python3.pkgs.callPackage ./default.nix {
          inherit (self'.packages) clan-cli-docs inventory-api-docs;
          inherit (inputs) nixpkgs;
          inherit module-docs;
          inherit asciinema-player-js;
          inherit asciinema-player-css;
        };
        deploy-docs = pkgs.callPackage ./deploy-docs.nix { inherit (config.packages) docs; };
        inherit module-docs;
      };
    };
}
