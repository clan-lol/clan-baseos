{ config, lib, ... }:
let
  clanDir = config.clan.core.clanDir;
  machineDir = clanDir + "/machines/";
  inherit (config.clan.core) machineName;

  # Instances might be empty, if the module is not used via the inventory
  #
  # Type: { ${instanceName} :: { roles :: Roles } }
  #   Roles :: { ${role_name} :: { machines :: [string] } }
  instances = config.clan.inventory.services.borgbackup or { };

  allClients = lib.foldlAttrs (
    acc: _instanceName: instanceConfig:
    acc
    ++ (
      if (builtins.elem machineName instanceConfig.roles.server.machines) then
        instanceConfig.roles.client.machines
      else
        [ ]
    )
  ) [ ] instances;
in
{
  config.services.borgbackup.repos =
    let
      borgbackupIpMachinePath = machines: machineDir + machines + "/facts/borgbackup.ssh.pub";
      machinesMaybeKey = builtins.map (
        machine:
        let
          fullPath = borgbackupIpMachinePath machine;
        in
        if builtins.pathExists fullPath then
          machine
        else
          lib.warn ''
            Machine ${machine} does not have a borgbackup key at ${fullPath},
            run `clan facts generate ${machine}` to generate it.
          '' null
      ) allClients;

      machinesWithKey = lib.filter (x: x != null) machinesMaybeKey;

      hosts = builtins.map (machine: {
        name = machine;
        value = {
          path = "/var/lib/borgbackup/${machine}";
          authorizedKeys = [ (builtins.readFile (borgbackupIpMachinePath machine)) ];
        };
      }) machinesWithKey;
    in
    if (builtins.listToAttrs hosts) != [ ] then builtins.listToAttrs hosts else { };
}
