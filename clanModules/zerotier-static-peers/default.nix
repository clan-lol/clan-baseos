{
  lib,
  config,
  pkgs,
  ...
}:
let
  dir = config.clan.core.settings.directory;
  machineDir = dir + "/machines/";
  machinesFileSet = builtins.readDir machineDir;
  machines = lib.mapAttrsToList (name: _: name) machinesFileSet;

  zerotierNetworkIdPath = machines: machineDir + machines + "/facts/zerotier-network-id";
  networkIdsUnchecked = builtins.map (
    machine:
    let
      fullPath = zerotierNetworkIdPath machine;
    in
    if builtins.pathExists fullPath then builtins.readFile fullPath else null
  ) machines;
  networkIds = lib.filter (machine: machine != null) networkIdsUnchecked;
  networkId = if builtins.length networkIds == 0 then null else builtins.elemAt networkIds 0;
in
#TODO:trace on multiple found network-ids
#TODO:trace on no single found networkId
{
  options.clan.zerotier-static-peers = {
    excludeHosts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ config.clan.core.machineName ];
      description = "Hosts that should be excluded";
    };
    networkIps = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra zerotier network Ips that should be accepted";
    };
    networkIds = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      description = "Extra zerotier network Ids that should be accepted";
    };
  };

  config.systemd.services.zerotier-static-peers-autoaccept =
    let
      zerotierIpMachinePath = machines: machineDir + machines + "/facts/zerotier-ip";
      networkIpsUnchecked = builtins.map (
        machine:
        let
          fullPath = zerotierIpMachinePath machine;
        in
        if builtins.pathExists fullPath then machine else null
      ) machines;
      networkIps = lib.filter (machine: machine != null) networkIpsUnchecked;
      machinesWithIp = lib.filterAttrs (name: _: (lib.elem name networkIps)) machinesFileSet;
      filteredMachines = lib.filterAttrs (
        name: _: !(lib.elem name config.clan.zerotier-static-peers.excludeHosts)
      ) machinesWithIp;
      hosts = lib.mapAttrsToList (host: _: host) (
        lib.mapAttrs' (
          machine: _:
          let
            fullPath = zerotierIpMachinePath machine;
          in
          lib.nameValuePair (builtins.readFile fullPath) [ machine ]
        ) filteredMachines
      );
      allHostIPs = config.clan.zerotier-static-peers.networkIps ++ hosts;
    in
    lib.mkIf (config.clan.core.networking.zerotier.controller.enable) {
      wantedBy = [ "multi-user.target" ];
      after = [ "zerotierone.service" ];
      path = [ config.clan.core.clanPkgs.zerotierone ];
      serviceConfig.ExecStart = pkgs.writeScript "static-zerotier-peers-autoaccept" ''
        #!/bin/sh
        ${lib.concatMapStringsSep "\n" (host: ''
          ${config.clan.core.clanPkgs.zerotier-members}/bin/zerotier-members allow --member-ip ${host}
        '') allHostIPs}
        ${lib.concatMapStringsSep "\n" (host: ''
          ${config.clan.core.clanPkgs.zerotier-members}/bin/zerotier-members allow ${host}
        '') config.clan.zerotier-static-peers.networkIds}
      '';
    };

  config.clan.core.networking.zerotier.networkId = lib.mkDefault networkId;
}
