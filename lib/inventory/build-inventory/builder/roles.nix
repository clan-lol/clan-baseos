{
  lib,
  config,
  resolveTags,
  inventory,
  clan-core,
  machineName,
  serviceConfigs,
  ...
}:
let
  serviceName = config.serviceName;
in
{
  # Roles resolution
  # : List String
  supportedRoles = clan-core.lib.modules.getRoles inventory.modules serviceName;
  matchedRoles = builtins.attrNames (
    lib.filterAttrs (_: ms: builtins.elem machineName ms) config.machinesRoles
  );
  resolvedRolesPerInstance = lib.mapAttrs (
    instanceName: instanceConfig:
    let
      resolvedRoles = lib.genAttrs config.supportedRoles (
        roleName:
        resolveTags {
          members = instanceConfig.roles.${roleName} or { };
          inherit
            instanceName
            serviceName
            roleName
            inventory
            ;
        }
      );
      usedRoles = builtins.attrNames instanceConfig.roles;
      unmatchedRoles = builtins.filter (role: !builtins.elem role config.supportedRoles) usedRoles;
    in
    if unmatchedRoles != [ ] then
      throw ''
        Roles ${builtins.toJSON unmatchedRoles} are not defined in the service ${serviceName}.
        Instance: '${instanceName}'
        Please use one of available roles: ${builtins.toJSON config.supportedRoles}
      ''
    else
      resolvedRoles
  ) serviceConfigs;

  machinesRoles = builtins.zipAttrsWith (
    _n: vs:
    let
      flat = builtins.foldl' (acc: s: acc ++ s.machines) [ ] vs;
    in
    lib.unique flat
  ) (builtins.attrValues config.resolvedRolesPerInstance);

  assertions = lib.concatMapAttrs (
    instanceName: resolvedRoles:
    clan-core.lib.modules.checkConstraints {
      moduleName = serviceName;
      allModules = inventory.modules;
      inherit resolvedRoles instanceName;
    }
  ) config.resolvedRolesPerInstance;
}
