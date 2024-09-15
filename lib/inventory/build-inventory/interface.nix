{ config, lib, ... }:
let
  types = lib.types;

  metaOptions = {
    name = lib.mkOption { type = types.str; };
    description = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
    };
    icon = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
    };
  };
  metaOptionsWith = name: {
    name = lib.mkOption {
      type = types.str;
      default = name;
    };
    description = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
    };
    icon = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
    };
  };

  moduleConfig = lib.mkOption {
    default = { };
    type = types.attrsOf types.anything;
  };

  extraModulesOption = lib.mkOption {
    description = ''
      List of imported '.nix' expressions.

      Strings are interpreted relative to the 'directory' passed to buildClan.
      The import only happens if the machine is part of the service or role.

      Other types are passed through to the nixos configuration.

      ## Example

      To import the `special.nix` file

      ```
      . Clan Directory
      ├── flake.nix
      ...
      └── modules
          ├── special.nix
          └── ...
      ```

      ```nix
      {
        extraModules = [ "modules/special.nix" ];
      }
      ```

    '';
    default = [ ];
    type = types.listOf (
      types.oneOf [
        types.str
        types.anything
      ]
    );
  };
in
{
  imports = [ ./assertions.nix ];
  options = {
    assertions = lib.mkOption {
      type = types.listOf types.unspecified;
      internal = true;
      visible = false;
      default = [ ];
    };
    meta = metaOptions;

    machines = lib.mkOption {
      default = { };
      type = types.attrsOf (
        types.submodule (
          { name, ... }:
          {
            options = {
              inherit (metaOptionsWith name) name description icon;

              tags = lib.mkOption {

                default = [ ];
                apply = lib.unique;
                type = types.listOf types.str;
              };
              system = lib.mkOption {
                default = null;
                type = types.nullOr types.str;
              };
              deploy.targetHost = lib.mkOption {
                description = "Configuration for the deployment of the machine";
                default = null;
                type = types.nullOr types.str;
              };
            };
          }
        )
      );
    };

    services = lib.mkOption {
      default = { };
      type = types.attrsOf (
        types.attrsOf (
          types.submodule (
            { name, ... }:
            {
              options.meta = metaOptionsWith name;
              options.extraModules = extraModulesOption;
              options.config = moduleConfig;
              options.machines = lib.mkOption {
                default = { };
                type = types.attrsOf (
                  types.submodule {
                    options.extraModules = extraModulesOption;
                    options.config = moduleConfig;
                  }
                );
              };
              options.roles = lib.mkOption {
                default = { };
                type = types.attrsOf (
                  types.submodule {
                    options.machines = lib.mkOption {
                      default = [ ];
                      type = types.listOf types.str;
                    };
                    options.tags = lib.mkOption {
                      default = [ ];
                      apply = lib.unique;
                      type = types.listOf types.str;
                    };
                    options.config = moduleConfig;
                    options.extraModules = extraModulesOption;
                  }
                );
              };
            }
          )
        )
      );
    };
  };
}
