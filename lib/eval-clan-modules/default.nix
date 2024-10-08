{
  nixpkgs,
  clan-core,
  lib,
}:
let
  inherit (import nixpkgs { system = "x86_64-linux"; }) pkgs;

  inherit (clan-core) clanModules;

  baseModule = {
    imports = (import (pkgs.path + "/nixos/modules/module-list.nix")) ++ [
      {
        nixpkgs.hostPlatform = "x86_64-linux";
        clan.core.name = "dummy";
      }
    ];
  };

  # This function takes a list of module names and evaluates them
  # evalClanModules :: [ String ] -> { config, options, ... }
  evalClanModulesLegacy =
    modulenames:
    let
      evaled = lib.evalModules {
        modules = [
          baseModule
          {
            clan.core.clanDir = ./.;
          }
          clan-core.nixosModules.clanCore
        ] ++ (map (name: clanModules.${name}) modulenames);
      };
    in
    # lib.warn ''
    #   EvalClanModules doesn't respect role specific interfaces.

    #   The following {module}/default.nix file trying to be imported.

    #   Modules: ${builtins.toJSON modulenames}

    #   This might result in incomplete or incorrect interfaces.

    #   FIX: Use evalClanModuleWithRole instead.
    # ''
    evaled;

  /*
    This function takes a list of module names and evaluates them
    Returns a set of interfaces as described below:

    Fn :: { ${moduleName} = Module; } -> {
      ${moduleName} :: {
        ${roleName}: JSONSchema
      }
    }
  */
  evalClanModulesWithRoles =
    clanModules:
    let
      getRoles =
        modulePath:
        let
          rolesDir = "${modulePath}/roles";
        in
        if builtins.pathExists rolesDir then
          lib.pipe rolesDir [
            builtins.readDir
            (lib.filterAttrs (_n: v: v == "regular"))
            lib.attrNames
            (lib.filter (fileName: lib.hasSuffix ".nix" fileName))
            (map (fileName: lib.removeSuffix ".nix" fileName))
          ]
        else
          [ ];
      res = builtins.mapAttrs (
        moduleName: module:
        let
          # module must be a path to the clanModule root by convention
          # See: clanModules/flake-module.nix
          roles =
            assert lib.isPath module;
            getRoles module;
        in
        lib.listToAttrs (
          lib.map (role: {
            name = role;
            value =
              (lib.evalModules {
                modules = [
                  baseModule
                  clan-core.nixosModules.clanCore
                  # Role interface
                  (module + "/roles/${role}.nix")
                ];
              }).options.clan.${moduleName} or { };
          }) roles
        )
      ) clanModules;
    in
    res;
in
{
  evalClanModules = evalClanModulesLegacy;
  inherit evalClanModulesWithRoles;
}
