{ lib, self, ... }:
let
  types = lib.types;
in
{
  options = {
    # Required options
    directory = lib.mkOption {
      type = types.path;
      default = self;
      defaultText = "Root directory of the flake";
      description = ''
        The directory containing the clan.

        A typical directory structure could look like this:

        ```
        .
        ├── flake.nix
        ├── assets
        ├── machines
        ├── modules
        └── sops
        ```
      '';
    };

    specialArgs = lib.mkOption {
      type = types.attrsOf types.raw;
      default = { };
      description = "Extra arguments to pass to nixosSystem i.e. useful to make self available";
    };

    # Optional
    machines = lib.mkOption {
      type = types.attrsOf types.deferredModule;
      default = { };
      description = ''
        A mapping of machine names to their nixos configuration.

        ???+ example

            ```nix
            machines = {
              my-machine = {
                # Your nixos configuration
              };
            };
            ```
      '';
    };
    inventory = lib.mkOption {
      type = types.submodule { imports = [ ../inventory/build-inventory/interface.nix ]; };
      description = ''
        The `Inventory` submodule.

        For details see the [Inventory](./inventory.md) documentation.
      '';
    };

    # Meta
    meta = lib.mkOption {
      description = ''
        Global information about the clan.
      '';
      type = types.deferredModuleWith {
        staticModules = [ ../inventory/build-inventory/meta-interface.nix ];
      };
      default = { };
    };

    pkgsForSystem = lib.mkOption {
      type = types.functionTo (types.nullOr types.attrs);
      default = _: null;
      defaultText = "Lambda :: String -> { ... } | null";
      description = ''
        A function that maps from architecture to pkg. `( string -> pkgs )`

        If specified this nixpkgs will be only imported once for each system.
        This improves performance, but all nipxkgs.* options will be ignored.
      '';
    };

    # Outputs
    nixosConfigurations = lib.mkOption {
      # Hide from documentation.
      # Exposed at the top-level of the flake, clan.nixosConfigurations should not used by the user.
      # Instead, the user should use the `.#nixosConfigurations` attribute of the flake output.
      visible = false;
      type = types.lazyAttrsOf types.raw;
      default = { };
    };
    # flake.clanInternals
    clanInternals = lib.mkOption {
      # Hide from documentation. Exposes internals to the cli.
      visible = false;
      # type = types.raw;
      # ClanInternals
      type = types.submodule {
        options = {
          # Those options are interfaced by the CLI
          # We don't specify the type here, for better performance.
          inventory = lib.mkOption { type = lib.types.raw; };
          inventoryFile = lib.mkOption { type = lib.types.raw; };
          clanModules = lib.mkOption { type = lib.types.raw; };
          source = lib.mkOption { type = lib.types.raw; };
          meta = lib.mkOption { type = lib.types.raw; };
          all-machines-json = lib.mkOption { type = lib.types.raw; };
          machines = lib.mkOption { type = lib.types.raw; };
          machinesFunc = lib.mkOption { type = lib.types.raw; };
        };
      };
    };
  };
}
