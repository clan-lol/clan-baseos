{ lib, pkgs, ... }:
let
  inherit (lib) mkOption types;
in
{
  imports = [
    (lib.mkRemovedOptionModule [
      "clan"
      "core"
      "clanName"
    ] "clanName has been removed. Use clan.core.name instead.")
    (lib.mkRemovedOptionModule [
      "clan"
      "core"
      "clanIcon"
    ] "clanIcon has been removed. Use clan.core.icon instead.")

    (lib.mkRenamedOptionModule
      [ "clan" "core" "clanDir" ]
      [
        "clan"
        "core"
        "settings"
        "directory"
      ]
    )
  ];
  options.clan.core = {
    settings = mkOption {
      description = ''
        Settings of the clan.

        This is a read-only attribute-set available to the machines of the clan.
      '';
      type = types.submodule {
        options = {
          directory = lib.mkOption {
            type = lib.types.path;
            # documentation.nixos.extraModules = [
            #   ...
            #   clan-core.nixosModules.clanCore
            #   { clan.core.settings.directory = ./path/to/flake; }
            # ];
            description = ''
              the location of the flake repo, used to calculate the location of facts and secrets
            '';
          };
        };
      };
    };

    name = lib.mkOption {
      type = lib.types.str;
      description = ''
        the name of the clan
      '';
      # Set by the flake, so it's read-only in the maschine
      readOnly = true;
    };
    icon = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      description = ''
        the location of the clan icon
      '';
      # Set by the flake, so it's read-only in the maschine
      readOnly = true;
    };
    machineIcon = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = ''
        the location of the machine icon
      '';
    };
    machineDescription = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = ''
        the description of the machine
      '';
    };
    machineName = lib.mkOption {
      type = lib.types.str;
      default = "nixos";
      description = ''
        the name of the machine
      '';
    };
    clanPkgs = lib.mkOption {
      defaultText = "self.packages.${pkgs.system}";
      internal = true;
    };
  };
}
