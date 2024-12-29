{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

    clan.url = "https://git.clan.lol/clan/clan-core/archive/main.tar.gz";
    clan.inputs.nixpkgs.follows = "nixpkgs";
    clan.inputs.flake-parts.follows = "flake-parts";

    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } (
      { ... }:
      {
        systems = [
          "x86_64-linux"
          "aarch64-linux"
          "x86_64-darwin"
          "aarch64-darwin"
        ];

        imports = [
          ./checks.nix
          ./clan.nix
          ./devshells.nix
          ./formatter.nix
        ];
      }
    );
}
