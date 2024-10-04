{ lib, ... }:
let
  types = lib.types;

  metaOptions = {
    name = lib.mkOption { type = types.nullOr types.str; };
    description = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
      description = ''
        Optional freeform description
      '';
    };
    icon = lib.mkOption {
      default = null;
      type = types.nullOr types.str;
      description = ''
        Under construction, will be used for the UI
      '';
    };
  };
in
{
  options = metaOptions;
}
