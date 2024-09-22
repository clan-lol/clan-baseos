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
    };
    inventory = lib.mkOption {
      type = types.submodule { imports = [ ../inventory/build-inventory/interface.nix ]; };
    };

    # Meta
    meta = lib.mkOption {
      type = types.nullOr (
        types.submodule {
          options = {
            name = lib.mkOption {
              type = types.nullOr types.str;
              description = "Needs to be (globally) unique, as this determines the folder name where the flake gets downloaded to.";
            };
          };
        }
      );
      default = null;
    };

    pkgsForSystem = lib.mkOption {
      type = types.functionTo (types.nullOr types.attrs);
      default = _: null;
    };

    # Outputs
    nixosConfigurations = lib.mkOption {
      type = types.lazyAttrsOf types.raw;
      default = { };
    };
    # flake.clanInternals
    clanInternals = lib.mkOption {
      # type = types.raw;
      # ClanInternals
      type = types.submodule {
        options = {
          # Those options are interfaced by the CLI
          # We don't speficy the type here, for better performance.
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
