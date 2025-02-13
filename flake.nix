{
  description = "clan.lol base operating system";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";

    disko.url = "github:nix-community/disko";
    disko.inputs.nixpkgs.follows = "nixpkgs";

    nixos-facter-modules.url = "github:numtide/nixos-facter-modules";

    sops-nix.url = "github:pinpox/sops-nix/lazy-assertions";
    sops-nix.inputs.nixpkgs.follows = "nixpkgs";

    systems.url = "github:nix-systems/default";

    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    inputs@{
      flake-parts,
      nixpkgs,
      self,
      systems,
      ...
    }:
    let
      inherit (nixpkgs.lib)
        filter
        optional
        pathExists
        ;
    in
    flake-parts.lib.mkFlake { inherit inputs; } (
      { ... }:
      {
        clan = {
          meta.name = "clan-core";
        };

        systems = import systems;
        imports =
          # only importing existing paths allows to minimize the flake for test
          # by removing files
          filter pathExists [
            ./checks/flake-module.nix
            ./clanModules/flake-module.nix
            ./devShell.nix
            ./docs/nix/flake-module.nix
            ./flakeModules/flake-module.nix
            ./lib/filter-clan-core/flake-module.nix
            ./lib/flake-module.nix
            ./nixosModules/clanCore/vars/flake-module.nix
            ./nixosModules/flake-module.nix
            ./pkgs/flake-module.nix
            ./templates/flake-module.nix
          ]
          ++ [
            (if pathExists ./flakeModules/clan.nix then import ./flakeModules/clan.nix inputs.self else { })
          ]
          # Make treefmt-nix optional
          # This only works if you set inputs.clan-core.inputs.treefmt-nix.follows
          # to a non-empty input that doesn't export a flakeModule
          ++ optional (pathExists ./formatter.nix && inputs.treefmt-nix ? flakeModule) ./formatter.nix;
      }
    );
}
