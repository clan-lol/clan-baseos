{
  lib,
  config,
  resolvedRoles,
  moduleName,
  ...
}:
{
  imports = [
    ./interface.nix
  ];
  config.assertions = lib.foldl' (
    ass: roleName:
    let
      roleConstraints = config.roles.${roleName};
      members = resolvedRoles.${roleName}.machines;
      memberCount = builtins.length members;
      # Checks
      eqCheck =
        if roleConstraints.eq != null then
          [
            {
              assertion = memberCount == roleConstraints.eq;
              message = "The ${moduleName} module requires exactly ${builtins.toString roleConstraints.eq} '${roleName}', but found ${builtins.toString memberCount}: ${builtins.toString members}";
            }
          ]
        else
          [ ];

      minCheck =
        if roleConstraints.min > 0 then
          [
            {
              assertion = memberCount >= roleConstraints.min;
              message = "The ${moduleName} module requires at least ${builtins.toString roleConstraints.min} '${roleName}'s, but found ${builtins.toString memberCount}: ${builtins.toString members}";
            }
          ]
        else
          [ ];

      maxCheck =
        if roleConstraints.max != null then
          [
            {
              assertion = memberCount <= roleConstraints.max;
              message = "The ${moduleName} module allows at most for ${builtins.toString roleConstraints.max} '${roleName}'s, but found ${builtins.toString memberCount}: ${builtins.toString members}";
            }
          ]
        else
          [ ];
    in
    eqCheck ++ minCheck ++ maxCheck ++ ass
  ) [ ] (lib.attrNames config.roles);
}
