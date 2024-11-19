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
    visible = false;
  };
  options.roles = lib.mapAttrs (
    _name: _:
    mkOption {
      description = ''
        Sub-attributes of `${_name}` are constraints for the role.
      '';
      default = { };
      type = types.submoduleWith {
        modules = [
          {
            options = {
              max = mkOption {
                type = types.nullOr types.int;
                default = null;
                description = ''
                  Maximum number of instances of this role that can be assigned to a module of this type.
                '';
              };
              min = mkOption {
                type = types.int;
                default = 0;
                description = ''
                  Minimum number of instances of this role that must at least be assigned to a module of this type.
                '';
              };
            };
          }
        ];
      };
    }
  ) rolesAttrs;

  # The resulting assertions
  options.assertions = mkOption {
    visible = false;
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
