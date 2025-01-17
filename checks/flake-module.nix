{ self, lib, ... }:
let
  inherit (lib)
    filter
    pathExists
    ;
in
{
  imports = filter pathExists [
    ./backups/flake-module.nix
    ./devshell/flake-module.nix
    ./flash/flake-module.nix
    ./impure/flake-module.nix
    ./installation/flake-module.nix
    ./nixos-documentation/flake-module.nix
  ];
  perSystem =
    {
      pkgs,
      lib,
      self',
      ...
    }:
    {
      checks =
        let
          nixosTestArgs = {
            # reference to nixpkgs for the current system
            inherit pkgs;
            # this gives us a reference to our flake but also all flake inputs
            inherit self;
          };
          nixosTests = lib.optionalAttrs (pkgs.stdenv.isLinux) {
            # import our test
            secrets = import ./secrets nixosTestArgs;
            container = import ./container nixosTestArgs;
            # Deltachat is currently marked as broken
            # deltachat = import ./deltachat nixosTestArgs;
            borgbackup = import ./borgbackup nixosTestArgs;
            matrix-synapse = import ./matrix-synapse nixosTestArgs;
            mumble = import ./mumble nixosTestArgs;
            syncthing = import ./syncthing nixosTestArgs;
            zt-tcp-relay = import ./zt-tcp-relay nixosTestArgs;
            postgresql = import ./postgresql nixosTestArgs;
            wayland-proxy-virtwl = import ./wayland-proxy-virtwl nixosTestArgs;
          };

          flakeOutputs =
            lib.mapAttrs' (
              name: config: lib.nameValuePair "nixos-${name}" config.config.system.build.toplevel
            ) self.nixosConfigurations
            // lib.mapAttrs' (n: lib.nameValuePair "package-${n}") self'.packages
            // lib.mapAttrs' (n: lib.nameValuePair "devShell-${n}") self'.devShells
            // lib.mapAttrs' (name: config: lib.nameValuePair "home-manager-${name}" config.activation-script) (
              self'.legacyPackages.homeConfigurations or { }
            );
        in
        nixosTests // flakeOutputs;
      legacyPackages = {
        nixosTests =
          let
            nixosTestArgs = {
              # reference to nixpkgs for the current system
              inherit pkgs;
              # this gives us a reference to our flake but also all flake inputs
              inherit self;
            };
          in
          lib.optionalAttrs (pkgs.stdenv.isLinux) {
            # import our test
            secrets = import ./secrets nixosTestArgs;
            container = import ./container nixosTestArgs;
          };
      };
    };
}
