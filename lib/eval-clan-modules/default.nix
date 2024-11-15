{
  clan-core,
  lib,
  pkgs,
}:
let
  baseModule = {
    imports = (import (pkgs.path + "/nixos/modules/module-list.nix")) ++ [
      {
        nixpkgs.pkgs = pkgs;
        clan.core.name = "dummy";
        system.stateVersion = lib.version;
      }
    ];
  };

  # This function takes a list of module names and evaluates them
  # evalClanModules :: [ module ] -> { config, options, ... }
  evalClanModulesLegacy =
    modules:
    let
      evaled = lib.evalModules {
        modules = [
          baseModule
          {
            clan.core.clanDir = clan-core;
          }
          clan-core.nixosModules.clanCore
        ] ++ modules;
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
      res = builtins.mapAttrs (
        moduleName: module:
        let
          frontmatter = clan-core.lib.modules.getFrontmatter moduleName;
          roles =
            if builtins.elem "inventory" frontmatter.features or [ ] then
              assert lib.isPath module;
              clan-core.lib.modules.getRoles moduleName
            else
              [ ];
        in
        lib.listToAttrs (
          lib.map (role: {
            name = role;
            value =
              (lib.evalModules {
                modules = [
                  baseModule
                  clan-core.nixosModules.clanCore
                  {
                    clan.core.clanDir = clan-core;
                  }
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
