# Integrity validation of the inventory
{ config, lib, ... }:
{
  # Assertion must be of type
  #  { assertion :: bool, message :: string, severity :: "error" | "warning" }
  imports = [
    # Check that each machine used in a service is defined in the top-level machines
    {
      assertions = lib.foldlAttrs (
        ass1: serviceName: c:
        ass1
        ++ lib.foldlAttrs (
          ass2: instanceName: instanceConfig:
          let
            topLevelMachines = lib.attrNames config.machines;
            # All machines must be defined in the top-level machines
            assertions = lib.foldlAttrs (
              assertions: roleName: role:
              assertions
              ++ builtins.filter (a: !a.assertion) (
                builtins.map (m: {
                  assertion = builtins.elem m topLevelMachines;
                  message = ''
                    Machine '${m}' is not defined in the inventory. This might still work, if the machine is defined via nix.

                    Defined in service: '${serviceName}' instance: '${instanceName}' role: '${roleName}'.

                    Inventory machines:
                    ${builtins.concatStringsSep "\n" (map (n: "'${n}'") topLevelMachines)}
                  '';
                  severity = "warning";
                }) role.machines
              )
            ) [ ] instanceConfig.roles;
          in
          ass2 ++ assertions
        ) [ ] c
      ) [ ] config.services;
    }
    # Check that each tag used in a role is defined in at least one machines tags
    {
      assertions = lib.foldlAttrs (
        ass1: serviceName: c:
        ass1
        ++ lib.foldlAttrs (
          ass2: instanceName: instanceConfig:
          let
            allTags = lib.foldlAttrs (
              tags: _machineName: machine:
              tags ++ machine.tags
            ) [ ] config.machines;
            # All machines must be defined in the top-level machines
            assertions = lib.foldlAttrs (
              assertions: roleName: role:
              assertions
              ++ builtins.filter (a: !a.assertion) (
                builtins.map (m: {
                  assertion = builtins.elem m allTags;
                  message = ''
                    Tag '${m}' is not defined in the inventory.

                    Defined in service: '${serviceName}' instance: '${instanceName}' role: '${roleName}'.

                    Available tags:
                    ${builtins.concatStringsSep "\n" (map (n: "'${n}'") allTags)}
                  '';
                  severity = "error";
                }) role.tags
              )
            ) [ ] instanceConfig.roles;
          in
          ass2 ++ assertions
        ) [ ] c
      ) [ ] config.services;
    }
  ];

}
