{
  lib,
  allRoles,
  moduleName,
  ...
}:
let
  inherit (lib) mkOption types;
  rolesAttrs = builtins.groupBy lib.id allRoles;
in
{
  options.serviceName = mkOption {
    type = types.str;
    default = moduleName;
    readOnly = true;
  };
  options.roles = lib.mapAttrs (
    _name: _:
    mkOption {
      default = { };
      type = types.submoduleWith {
        modules = [
          {
            options = {
              max = mkOption {
                type = types.nullOr types.int;
                default = null;
              };
              min = mkOption {
                type = types.int;
                default = 0;
              };
            };
          }
        ];
      };
    }
  ) rolesAttrs;

  options.instances = mkOption {
    default = { };
    type = types.submoduleWith {
      modules = [
        {
          options = {
            max = mkOption {
              type = types.nullOr types.int;
              default = null;
            };
          };
        }
      ];
    };
  };

  # The resulting assertions
  options.assertions = mkOption {
    default = { };
    type = types.attrsOf (
      types.submoduleWith {
        modules = [
          {
            options = {
              assertion = mkOption {
                type = types.bool;
              };
              message = mkOption {
                type = types.str;
              };
            };
          }
        ];
      }
    );
  };
}
