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

  /*
    Returns a NixOS configuration for every machine in the inventory.

    machinesFromInventory :: Inventory -> { ${machine_name} :: NixOSConfiguration }
  */

  # { client_1_machine = { tags = [ "backup" ]; }; client_2_machine = { tags = [ "backup" ]; }; not_used_machine = { }; }
  getAllMachines =
    inventory:
    lib.foldlAttrs (
      res: serviceName: serviceConfigs:
      (lib.foldlAttrs (
        res: instanceName: serviceConfig:
        lib.foldlAttrs (
          res: roleName: members:
          let
            resolved = resolveTags {
              inherit
                serviceName
                instanceName
                roleName
                inventory
                members
                ;
            };
          in
          res
          // builtins.listToAttrs (
            builtins.map (m: {
              name = m;
              value = { };
            }) resolved.machines
          )
        ) res serviceConfig.roles
      ) res serviceConfigs)
    ) { } (inventory.services or { })
    // inventory.machines or { };

  buildInventory =
    { inventory, directory }:
    # For every machine in the inventory, build a NixOS configuration
    # For each machine generate config, forEach service, if the machine is used.
    builtins.mapAttrs (
      machineName: machineConfig:
      lib.foldlAttrs (
        # [ Modules ], String, { ${instance_name} :: ServiceConfig }
        acc: serviceName: serviceConfigs:
        acc
        # Collect service config
        ++ (lib.foldlAttrs (
          # [ Modules ], String, ServiceConfig
          acc2: instanceName: serviceConfig:
          let
            resolvedRoles = builtins.mapAttrs (
              roleName: members:
              resolveTags {
                inherit
                  serviceName
                  instanceName
                  roleName
                  inventory
                  members
                  ;
              }
            ) serviceConfig.roles;

            isInService = builtins.any (members: builtins.elem machineName members.machines) (
              builtins.attrValues resolvedRoles
            );

            # Inverse map of roles. Allows for easy lookup of roles for a given machine.
            # { ${machine_name} :: [roles]
            inverseRoles = lib.foldlAttrs (
              acc: roleName:
              { machines }:
              acc
              // builtins.foldl' (
                acc2: machineName: acc2 // { ${machineName} = (acc.${machineName} or [ ]) ++ [ roleName ]; }
              ) { } machines
            ) { } resolvedRoles;

            machineServiceConfig = (serviceConfig.machines.${machineName} or { }).config or { };
            globalConfig = serviceConfig.config or { };

            globalImports = serviceConfig.imports or [ ];
            machineImports = serviceConfig.machines.${machineName}.imports or [ ];
            roleServiceImports = builtins.foldl' (
              acc: role: acc ++ serviceConfig.roles.${role}.imports or [ ]
            ) [ ] inverseRoles.${machineName} or [ ];

            # TODO: maybe optimize this dont lookup the role in inverse roles. Imports are not lazy
            roleModules = builtins.map (
              role:
              let
                path = "${clan-core.clanModules.${serviceName}}/roles/${role}.nix";
              in
              if builtins.pathExists path then
                path
              else if role == "default" then
                { }
              else
                throw "Module doesn't have role: '${role}'. Path: ${path} not found."
            ) inverseRoles.${machineName} or [ ];

            roleServiceConfigs = builtins.filter (m: m != { }) (
              builtins.map (role: serviceConfig.roles.${role}.config or { }) inverseRoles.${machineName} or [ ]
            );

            customImports = map (s: "${directory}/${s}") (
              globalImports ++ machineImports ++ roleServiceImports
            );
          in

          if isInService then
            acc2
            ++ [
              {
                imports = [ clan-core.clanModules.${serviceName} ] ++ roleModules ++ customImports;
              }
              (lib.optionalAttrs (globalConfig != { } || machineServiceConfig != { } || roleServiceConfigs != [ ])
                {
                  config.clan.${serviceName} = lib.mkMerge (
                    [
                      (globalConfig)
                      (lib.traceValSeq machineServiceConfig)
                    ]
                    ++ (roleServiceConfigs)
                  );
                }
              )

              {
                config.clan.inventory.services.${serviceName}.${instanceName} = {
                  roles = resolvedRoles;
                  # TODO: Add inverseRoles to the service config if needed
                  # inherit inverseRoles;
                };
              }
            ]
          else
            acc2
        ) [ ] serviceConfigs)
      ) [ ] inventory.services
      # Append each machine config
      ++ [
        (lib.optionalAttrs (machineConfig.system or null != null) {
          config.nixpkgs.hostPlatform = machineConfig.system;
        })
        (lib.optionalAttrs (machineConfig.deploy.targetHost or null != null) {
          config.clan.core.networking.targetHost = machineConfig.deploy.targetHost;
        })
      ]
    ) (getAllMachines inventory);
in
{
  inherit buildInventory getAllMachines;
}
