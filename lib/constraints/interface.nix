{ lib, allRoles, ... }:
let
  inherit (lib) mkOption types;
  rolesAttrs = builtins.groupBy lib.id allRoles;
in
{
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
              eq = mkOption {
                type = types.nullOr types.int;
                default = null;
              };
            };
          }
        ];
      };
    }
  ) rolesAttrs;

  # The resulting assertions
  options.assertions = mkOption {
    default = [ ];
    type = types.listOf (
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
