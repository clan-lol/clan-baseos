# Generate partial NixOS configurations for every machine in the inventory
# This function is responsible for generating the module configuration for every machine in the inventory.
{ lib, clan-core }:
let
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
            throw ''
              inventory.services.${serviceName}.${instanceName}: - ${roleName} tags: no machine with tag '${tag}' found.
              Available tags: ${builtins.toJSON (lib.unique availableTags)}
            ''
          else
            acc ++ tagMembers
        ) [ ] members.tags or [ ]);
    };

  checkService =
    modulepath: serviceName:
    builtins.elem "inventory"
      (clan-core.lib.modules.getFrontmatter modulepath serviceName).features or [ ];

  extendMachine =
    { machineConfig, inventory }:
    [
      (lib.optionalAttrs (machineConfig.deploy.targetHost or null != null) {
        config.clan.core.networking.targetHost = machineConfig.deploy.targetHost;
      })
      {
        assertions = lib.foldlAttrs (
          acc: serviceName: _serviceConfigs:
          acc
          ++ [
            {
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
            }
          ]
        ) [ ] inventory.services;
      }
    ];

  mapMachineConfigToNixOSConfig =
    # Returns a NixOS configuration for the machine 'machineName'.
    # Return Format: { imports = [ ... ]; config = { ... }; options = { ... } }
    {
      machineName,
      machineConfig,
      inventory,
      directory,
    }:
    lib.foldlAttrs (
      # [ Modules ], String, { ${instance_name} :: ServiceConfig }
      initialServiceModules: serviceName: serviceConfigs:
      initialServiceModules
      # Collect service config
      ++ (lib.foldlAttrs (
        # [ Modules ], String, ServiceConfig
        acc2: instanceName: serviceConfig:

        let
          roles = clan-core.lib.modules.getRoles inventory.modules serviceName;

          resolvedRoles = lib.genAttrs roles (
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
            if builtins.elem role roles && inventory.modules ? ${serviceName} then
              inventory.modules.${serviceName} + "/roles/${role}.nix"
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

          nonExistingRoles = builtins.filter (role: !(builtins.elem role roles)) (
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
      ) [ ] (serviceConfigs))
    ) [ ] inventory.services
    # Global extension for each machine
    ++ (extendMachine { inherit machineConfig inventory; });
  /*
    Returns a NixOS configuration for every machine in the inventory.

    machinesFromInventory :: Inventory -> { ${machine_name} :: NixOSConfiguration }
  */
  buildInventory =
    { inventory, directory }:
    # For every machine in the inventory, build a NixOS configuration
    # For each machine generate config, forEach service, if the machine is used.
    builtins.mapAttrs (
      machineName: machineConfig:
      mapMachineConfigToNixOSConfig {
        inherit
          machineName
          machineConfig
          inventory
          directory
          ;
      }
    ) (inventory.machines or { });
in
{
  inherit buildInventory;
}
