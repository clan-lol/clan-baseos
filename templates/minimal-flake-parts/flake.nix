{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";

    clan.url = "git+https://git.clan.lol/clan/clan-core?shallow=1";
    clan.inputs.nixpkgs.follows = "nixpkgs";
    clan.inputs.flake-parts.follows = "flake-parts";

    flake-parts.url = "github:hercules-ci/flake-parts?shallow=1";
    flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";

  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } (
      { ... }:
      {
        systems = [
          "x86_64-linux"
        ];

        imports = [
          ./checks.nix
          ./clan.nix
          ./devshells.nix
        ];
      }
    );
}
