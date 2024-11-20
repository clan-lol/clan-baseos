{
  modulesRolesOptions,
  nixosOptionsDoc,
  clanModules,
  evalClanModules,
  lib,
}:
{
  # clanModules docs
  clanModulesViaNix = lib.mapAttrs (
    name: module:
    if builtins.pathExists (module + "/default.nix") then
      (nixosOptionsDoc {
        options = ((evalClanModules [ module ]).options).clan.${name} or { };
        warningsAreErrors = true;
      }).optionsJSON
    else
      { }
  ) clanModules;

  clanModulesViaRoles = lib.mapAttrs (
    _moduleName: rolesOptions:
    lib.mapAttrs (
      _roleName: options:
      (nixosOptionsDoc {
        inherit options;
        warningsAreErrors = true;
      }).optionsJSON
    ) rolesOptions
  ) modulesRolesOptions;

  clanCore =
    (nixosOptionsDoc {
      options = ((evalClanModules [ ]).options).clan.core or { };
      warningsAreErrors = true;
    }).optionsJSON;
}
