{
  lib,
  config,
  clan-core,
  ...
}:
let
  inherit (config) inventory directory;
  resolveTags =
    # Inventory, { machines :: [string], tags :: [string] }
    {
      serviceName,
      instanceName,
      roleName,
      inventory,
      members,
    }:
    {
      machines =
        members.machines or [ ]
        ++ (builtins.foldl' (
          acc: tag:
          let
            # For error printing
            availableTags = lib.foldlAttrs (
              acc: _: v:
              v.tags or [ ] ++ acc
            ) [ ] (inventory.machines);

            tagMembers = builtins.attrNames (
              lib.filterAttrs (_n: v: builtins.elem tag v.tags or [ ]) inventory.machines
            );
          in
          if tagMembers == [ ] then
            lib.warn ''
              inventory.services.${serviceName}.${instanceName}: - ${roleName} tags: no machine with tag '${tag}' found.
              Available tags: ${builtins.toJSON (lib.unique availableTags)}
            '' [ ]
          else
            acc ++ tagMembers
        ) [ ] members.tags or [ ]);
    };

  checkService =
    modulepath: serviceName:
    builtins.elem "inventory"
      (clan-core.lib.modules.getFrontmatter modulepath serviceName).features or [ ];

  compileMachine =
    { machineConfig }:
    {
      machineImports = [
        (lib.optionalAttrs (machineConfig.deploy.targetHost or null != null) {
          config.clan.core.networking.targetHost = machineConfig.deploy.targetHost;
        })
      ];
      assertions = { };
    };

  legacyResolveImports =
    {
      supportedRoles,
      serviceConfigs,
      serviceName,
      machineName,
      getRoleFile,
    }:
    (lib.foldlAttrs (
      # : [ Modules ] -> String -> ServiceConfig -> [ Modules ]
      acc2: instanceName: serviceConfig:
      let
        resolvedRoles = lib.genAttrs supportedRoles (
          roleName:
          resolveTags {
            members = serviceConfig.roles.${roleName} or { };
            inherit
              serviceName
              instanceName
              roleName
              inventory
              ;
          }
        );

        isInService = builtins.any (members: builtins.elem machineName members.machines) (
          builtins.attrValues resolvedRoles
        );

        # all roles where the machine is present
        machineRoles = builtins.attrNames (
          lib.filterAttrs (_role: roleConfig: builtins.elem machineName roleConfig.machines) resolvedRoles
        );
        machineServiceConfig = (serviceConfig.machines.${machineName} or { }).config or { };
        globalConfig = serviceConfig.config or { };

        globalExtraModules = serviceConfig.extraModules or [ ];
        machineExtraModules = serviceConfig.machines.${machineName}.extraModules or [ ];
        roleServiceExtraModules = builtins.foldl' (
          acc: role: acc ++ serviceConfig.roles.${role}.extraModules or [ ]
        ) [ ] machineRoles;

        # TODO: maybe optimize this dont lookup the role in inverse roles. Imports are not lazy
        roleModules = builtins.map (
          role:
          if builtins.elem role supportedRoles && inventory.modules ? ${serviceName} then
            getRoleFile role
          else
            throw "Module ${serviceName} doesn't have role: '${role}'. Role: ${
              inventory.modules.${serviceName}
            }/roles/${role}.nix not found."
        ) machineRoles;

        roleServiceConfigs = builtins.filter (m: m != { }) (
          builtins.map (role: serviceConfig.roles.${role}.config or { }) machineRoles
        );

        extraModules = map (s: if builtins.typeOf s == "string" then "${directory}/${s}" else s) (
          globalExtraModules ++ machineExtraModules ++ roleServiceExtraModules
        );

        nonExistingRoles = builtins.filter (role: !(builtins.elem role supportedRoles)) (
          builtins.attrNames (serviceConfig.roles or { })
        );

        constraintAssertions = clan-core.lib.modules.checkConstraints {
          moduleName = serviceName;
          allModules = inventory.modules;
          inherit resolvedRoles instanceName;
        };
      in
      if (nonExistingRoles != [ ]) then
        throw "Roles ${builtins.toString nonExistingRoles} are not defined in the service ${serviceName}."
      else if !(serviceConfig.enabled or true) then
        acc2
      else if isInService then
        acc2
        ++ [
          {
            imports = roleModules ++ extraModules;

            clan.inventory.assertions = constraintAssertions;
            clan.inventory.services.${serviceName}.${instanceName} = {
              roles = resolvedRoles;
              # TODO: Add inverseRoles to the service config if needed
              # inherit inverseRoles;
            };
          }
          (lib.optionalAttrs (globalConfig != { } || machineServiceConfig != { } || roleServiceConfigs != [ ])
            {
              clan.${serviceName} = lib.mkMerge (
                [
                  globalConfig
                  machineServiceConfig
                ]
                ++ roleServiceConfigs
              );
            }
          )
        ]
      else
        acc2
    ) [ ] (serviceConfigs));
in
{
  imports = [ ./interface.nix ];
  config = {
    machines = builtins.mapAttrs (
      machineName: machineConfig: m:
      let
        compiledServices = lib.mapAttrs (
          _: serviceConfigs:
          (
            { config, ... }:
            let
              serviceName = config.serviceName;
              loadModuleForClassCheck =
                m:
                if lib.isFunction m then
                  let
                    args = lib.functionArgs m;
                  in
                  m args
                else
                  m;
              firstRole = import (getRoleFile (builtins.head config.supportedRoles));
              getRoleFile = role: builtins.seq role inventory.modules.${serviceName} + "/roles/${role}.nix";

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
                    Service: '${serviceName}' Instance: '${instanceName}'
                    The following roles do not exist: ${builtins.toJSON unmatchedRoles}
                    Please use one of available roles: ${builtins.toJSON config.supportedRoles}
                  ''
                else
                  resolvedRoles
              ) serviceConfigs;
            in
            {
              # Roles resolution
              # : List String
              supportedRoles = clan-core.lib.modules.getRoles inventory.modules serviceName;
              matchedRoles = builtins.attrNames (
                lib.filterAttrs (_: ms: builtins.elem machineName ms) config.machinesRoles
              );
              inherit resolvedRolesPerInstance;
              isClanModule =
                let
                  module = loadModuleForClassCheck firstRole;
                in
                if module ? _class then module._class == "clan" else false;

              machinesRoles = builtins.zipAttrsWith (
                _n: vs:
                let
                  flat = builtins.foldl' (acc: s: acc ++ s.machines) [ ] vs;
                in
                lib.unique flat
              ) (builtins.attrValues resolvedRolesPerInstance);

              # The actual result
              machineImports =
                if config.isClanModule then
                  throw "Clan modules are not supported yet."
                else
                  legacyResolveImports {
                    supportedRoles = config.supportedRoles;
                    inherit
                      serviceConfigs
                      serviceName
                      machineName
                      getRoleFile
                      ;
                  };

              # Assertions
              assertions = {
                "checkservice.${serviceName}" = {
                  assertion = checkService inventory.modules.${serviceName} serviceName;
                  message = ''
                    Service ${serviceName} cannot be used in inventory. It does not declare the 'inventory' feature.

                    To allow it add the following to the beginning of the README.md of the module:

                      ---
                      ...

                      features = [ "inventory" ]
                      ---

                    Also make sure to test the module with the 'inventory' feature enabled.

                  '';
                };
              };
            }
          )
        ) (config.inventory.services or { });

        compiledMachine = compileMachine {
          inherit
            machineConfig
            ;
        };

        machineImports =
          compiledMachine.machineImports
          ++ builtins.foldl' (
            acc: service:
            let
              failedAssertions = (lib.filterAttrs (_: v: !v.assertion) service.assertions);
              failedAssertionsImports =
                if failedAssertions != { } then
                  [
                    {
                      clan.inventory.assertions = failedAssertions;
                    }
                  ]
                else
                  [ ];
            in
            acc
            ++ service.machineImports
            # Import failed assertions
            ++ failedAssertionsImports
          ) [ ] (builtins.attrValues m.config.compiledServices);

      in
      {
        inherit machineImports compiledServices compiledMachine;
      }
    ) (inventory.machines or { });
  };

}
