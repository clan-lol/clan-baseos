{ lib, config, ... }:
let
  dir = config.clan.core.settings.directory;
  machineDir = dir + "/machines/";
in
{
  imports = [ ../borgbackup ];

  options.clan.borgbackup-static = {
    excludeMachines = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      example = [ config.clan.core.machineName ];
      default = [ ];
      description = ''
        Machines that should not be backuped.
        Mutually exclusive with includeMachines.
        If this is not empty, every other machine except the targets in the clan will be backuped by this module.
        If includeMachines is set, only the included machines will be backuped.
      '';
    };
    includeMachines = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      example = [ config.clan.core.machineName ];
      default = [ ];
      description = ''
        Machines that should be backuped.
        Mutually exclusive with excludeMachines.
      '';
    };
    targets = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = ''
        Machines that should act as target machines for backups.
      '';
    };
  };

  config.services.borgbackup.repos =
    let
      machines = builtins.readDir machineDir;
      borgbackupIpMachinePath = machines: machineDir + machines + "/facts/borgbackup.ssh.pub";
      filteredMachines =
        if ((builtins.length config.clan.borgbackup-static.includeMachines) != 0) then
          lib.filterAttrs (name: _: (lib.elem name config.clan.borgbackup-static.includeMachines)) machines
        else
          lib.filterAttrs (name: _: !(lib.elem name config.clan.borgbackup-static.excludeMachines)) machines;
      machinesMaybeKey = lib.mapAttrsToList (
        machine: _:
        let
          fullPath = borgbackupIpMachinePath machine;
        in
        if builtins.pathExists fullPath then machine else null
      ) filteredMachines;
      machinesWithKey = lib.filter (x: x != null) machinesMaybeKey;
      hosts = builtins.map (machine: {
        name = machine;
        value = {
          path = "/var/lib/borgbackup/${machine}";
          authorizedKeys = [ (builtins.readFile (borgbackupIpMachinePath machine)) ];
        };
      }) machinesWithKey;
    in
    lib.mkIf
      (builtins.any (
        target: target == config.clan.core.machineName
      ) config.clan.borgbackup-static.targets)
      (if (builtins.listToAttrs hosts) != null then builtins.listToAttrs hosts else { });

  config.clan.borgbackup.destinations =
    let
      destinations = builtins.map (d: {
        name = d;
        value = {
          repo = "borg@${d}:/var/lib/borgbackup/${config.clan.core.machineName}";
        };
      }) config.clan.borgbackup-static.targets;
    in
    lib.mkIf (builtins.any (
      target: target == config.clan.core.machineName
    ) config.clan.borgbackup-static.includeMachines) (builtins.listToAttrs destinations);

  config.assertions = [
    {
      assertion =
        !(
          ((builtins.length config.clan.borgbackup-static.excludeMachines) != 0)
          && ((builtins.length config.clan.borgbackup-static.includeMachines) != 0)
        );
      message = ''
        The options:
        config.clan.borgbackup-static.excludeMachines = [${builtins.toString config.clan.borgbackup-static.excludeMachines}]
        and
        config.clan.borgbackup-static.includeMachines = [${builtins.toString config.clan.borgbackup-static.includeMachines}]
        are mutually exclusive.
        Use excludeMachines to exclude certain machines and backup the other clan machines.
        Use include machines to only backup certain machines.
      '';
    }
  ];
  config.warnings = lib.optional (
    builtins.length config.clan.borgbackup-static.targets > 0
  ) "The borgbackup-static module is deprecated use the service via the inventory interface instead.";
}
