{
  config,
  lib,
  pkgs,
  ...
}:
{
  options.clan.packages = {
    packages = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      description = "The packages to install on the machine";
    };
  };
  config = {
    environment.systemPackages = map (
      pName: lib.getAttrFromPath (lib.splitString "." pName) pkgs
    ) config.clan.packages.packages;
  };
}
