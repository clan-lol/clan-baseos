{
  lib,
  config,
  resolvedRoles,
  instanceName,
  moduleName,
  ...
}:
let
  inherit (config) roles;
in
{
  imports = [
    ./interface.nix
    # Role assertions
    {
      config.assertions = lib.foldlAttrs (
        ass: roleName: roleConstraints:
        let
          members = resolvedRoles.${roleName}.machines;
          memberCount = builtins.length members;
          # Checks
          minCheck = lib.optionalAttrs (roleConstraints.min > 0) {
            "${moduleName}.${instanceName}.roles.${roleName}.min" = {
              assertion = memberCount >= roleConstraints.min;
              message = ''
                The ${moduleName} module requires at least ${builtins.toString roleConstraints.min} members of the '${roleName}' role
                but found '${builtins.toString memberCount}' members within instance '${instanceName}':

                ${lib.concatLines members}
              '';
            };
          };

          maxCheck = lib.optionalAttrs (roleConstraints.max != null) {
            "${moduleName}.${instanceName}.roles.${roleName}.max" = {
              assertion = memberCount <= roleConstraints.max;
              message = ''
                The ${moduleName} module allows at most for ${builtins.toString roleConstraints.max} members of the '${roleName}' role
                but found '${builtins.toString memberCount}' members within instance '${instanceName}':

                ${lib.concatLines members}
              '';
            };
          };

        in
        ass // maxCheck // minCheck
      ) { } roles;
    }
  ];
}
