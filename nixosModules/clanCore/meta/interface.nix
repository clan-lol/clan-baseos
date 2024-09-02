{ lib, ... }:
let
  optStr = lib.types.nullOr lib.types.str;
in
{
  options.clan.meta.name = lib.mkOption {
    description = "The name of the clan";
    type = lib.types.str;
  };
  options.clan.meta.description = lib.mkOption {
    description = "The description of the clan";
    type = optStr;
  };
  options.clan.meta.icon = lib.mkOption {
    description = "The location of the clan icon";
    type = optStr;
  };
}
