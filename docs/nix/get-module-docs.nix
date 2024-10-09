{
  nixosOptionsDoc,
  clanModules,
  evalClanModules,
  lib,
}:
{
  # clanModules docs
  clanModules = lib.mapAttrs (
    name: module:
    (nixosOptionsDoc {
      options = ((evalClanModules [ module ]).options).clan.${name} or { };
      warningsAreErrors = true;
    }).optionsJSON
  ) clanModules;

  clanCore =
    (nixosOptionsDoc {
      options = ((evalClanModules [ ]).options).clan.core or { };
      warningsAreErrors = true;
    }).optionsJSON;
}
