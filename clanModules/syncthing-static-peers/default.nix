{
  lib,
  config,
  pkgs,
  ...
}:
let
  dir = config.clan.core.settings.directory;
  machineDir = dir + "/machines/";
  machineVarDir = dir + "/vars/per-machine/";
  syncthingPublicKeyPath = machines: machineVarDir + machines + "/syncthing/id/value";
  machinesFileSet = builtins.readDir machineDir;
  machines = lib.mapAttrsToList (name: _: name) machinesFileSet;
  syncthingPublicKeysUnchecked = builtins.map (
    machine:
    let
      fullPath = syncthingPublicKeyPath machine;
    in
    if builtins.pathExists fullPath then machine else null
  ) machines;
  syncthingPublicKeyMachines = lib.filter (machine: machine != null) syncthingPublicKeysUnchecked;
  zerotierIpMachinePath = machines: machineDir + machines + "/facts/zerotier-ip";
  networkIpsUnchecked = builtins.map (
    machine:
    let
      fullPath = zerotierIpMachinePath machine;
    in
    if builtins.pathExists fullPath then machine else null
  ) machines;
  networkIpMachines = lib.filter (machine: machine != null) networkIpsUnchecked;
  devices = builtins.map (machine: {
    name = machine;
    value = {
      name = machine;
      id = (lib.removeSuffix "\n" (builtins.readFile (syncthingPublicKeyPath machine)));
      addresses =
        [ "dynamic" ]
        ++ (
          if (lib.elem machine networkIpMachines) then
            [ "tcp://[${(lib.removeSuffix "\n" (builtins.readFile (zerotierIpMachinePath machine)))}]:22000" ]
          else
            [ ]
        );
    };
  }) syncthingPublicKeyMachines;
in
{
  options.clan.syncthing-static-peers = {
    excludeMachines = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      example = [ config.clan.core.settings.machine.name ];
      default = [ ];
      description = ''
        Machines that should not be added.
      '';
    };
  };

  config.services.syncthing.settings.devices = (builtins.listToAttrs devices);

  imports = [
    {
      # Syncthing ports: 8384 for remote access to GUI
      # 22000 TCP and/or UDP for sync traffic
      # 21027/UDP for discovery
      # source: https://docs.syncthing.net/users/firewall.html
      networking.firewall.interfaces."zt+".allowedTCPPorts = [
        8384
        22000
      ];
      networking.firewall.allowedTCPPorts = [ 8384 ];
      networking.firewall.interfaces."zt+".allowedUDPPorts = [
        22000
        21027
      ];

      # Activates inotify compatibility on syncthing
      # use mkOverride 900 here as it otherwise would collide with the default of the
      # upstream nixos xserver.nix
      boot.kernel.sysctl."fs.inotify.max_user_watches" = lib.mkOverride 900 524288;

      services.syncthing = {
        enable = true;
        configDir = "/var/lib/syncthing";
        group = "syncthing";

        key = lib.mkDefault config.clan.core.vars.generators.syncthing.files.key.path or null;
        cert = lib.mkDefault config.clan.core.vars.generators.syncthing.files.cert.path or null;
      };

      clan.core.vars.generators.syncthing = {
        files.key = { };
        files.cert = { };
        files.api = { };
        files.id.secret = false;
        runtimeInputs = [
          pkgs.coreutils
          pkgs.gnugrep
          pkgs.syncthing
        ];
        script = ''
          syncthing generate --config $out
          mv $out/key.pem $out/key
          mv $out/cert.pem $out/cert
          cat $out/config.xml | grep -oP '(?<=<device id=")[^"]+' | uniq > $out/id
          cat $out/config.xml | grep -oP '<apikey>\K[^<]+' | uniq > $out/api
        '';
      };
    }
  ];
}
