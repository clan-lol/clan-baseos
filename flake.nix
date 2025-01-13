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
      self,
      systems,
      ...
    }:
    flake-parts.lib.mkFlake { inherit inputs; } (
      { ... }:
      {
        clan = {
          meta.name = "clan-core";
          directory = self;
        };
        systems = import systems;
        imports = [
          ./checks/flake-module.nix
          ./clanModules/flake-module.nix
          ./flakeModules/flake-module.nix
          (import ./flakeModules/clan.nix inputs.self)
          ./devShell.nix
          # TODO: migrate this @davHau
          # ./docs/flake-module
          ./docs/nix/flake-module.nix
          ./lib/flake-module.nix
          ./nixosModules/flake-module.nix
          ./nixosModules/clanCore/vars/flake-module.nix
          ./pkgs/flake-module.nix
          ./templates/flake-module.nix
          # Make treefmt-nix optional
          # This only works if you set inputs.clan-core.inputs.treefmt-nix.follows
          # to a non-empty input that doesn't export a flakeModule
        ] ++ inputs.nixpkgs.lib.optional (inputs.treefmt-nix ? flakeModule) ./formatter.nix;
      }
    );
}
