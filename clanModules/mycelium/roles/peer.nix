{
  pkgs,
  config,
  lib,
  ...
}:
let
  flake = config.clan.core.settings.directory;
  machineName = config.clan.core.settings.machine.name;

  # Instances might be empty, if the module is not used via the inventory
  #
  # Type: { ${instanceName} :: { roles :: Roles } }
  #   Roles :: { ${role_name} :: { machines :: [string] } }
  instances = config.clan.inventory.services.mycelium or { };

  allPeers = lib.foldlAttrs (
    acc: _instanceName: instanceConfig:
    acc
    ++ (
      if (builtins.elem machineName instanceConfig.roles.peer.machines) then
        instanceConfig.roles.peer.machines
      else
        [ ]
    )
  ) [ ] instances;
  allPeerConfigurations = lib.filterAttrs (n: _: builtins.elem n allPeers) flake.nixosConfigurations;
  allPeersWithIp =
    builtins.mapAttrs
      (_: x: lib.removeSuffix "\n" x.config.clan.core.vars.generators.mycelium.files.ip.value)
      (
        lib.filterAttrs (
          _: x: (builtins.tryEval x.config.clan.core.vars.generators.mycelium.files.ip.value).success
        ) allPeerConfigurations
      );

  ips = lib.attrValues allPeersWithIp;
  peers = lib.concatMap (ip: [
    "tcp://[${ip}]:9651"
    "quic://[${ip}]:9651"
  ]) ips;
in
{
  options = {
    clan.mycelium.topLevelDomain = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "Top level domain to reach hosts";
    };
    clan.mycelium.openFirewall = lib.mkEnableOption "Open the firewall for mycelium";
    clan.mycelium.addHostedPublicNodes = lib.mkEnableOption "Add hosted Public nodes";
    clan.mycelium.addHosts = lib.mkOption {
      default = true;
      description = "Add mycelium ip's to the host file";
    };
  };

  config.services.mycelium = {
    enable = true;
    addHostedPublicNodes = lib.mkDefault config.clan.mycelium.addHostedPublicNodes;
    openFirewall = lib.mkDefault config.clan.mycelium.openFirewall;
    keyFile = config.clan.core.vars.generators.mycelium.files.key.path;
    inherit peers;
  };

  config.networking.hosts = lib.mkIf (config.clan.mycelium.addHosts) (
    lib.mapAttrs' (
      host: ip:
      lib.nameValuePair ip (
        if (config.clan.mycelium.topLevelDomain == "") then [ host ] else [ "${host}.m" ]
      )
    ) allPeersWithIp
  );

  config.clan.core.vars.generators.mycelium = {
    files."key" = { };
    files."ip".secret = false;
    files."pubkey".secret = false;
    runtimeInputs = [
      pkgs.mycelium
      pkgs.coreutils
      pkgs.jq
    ];
    script = ''
      timeout 5 mycelium --key-file "$out"/key || :
      mycelium inspect --key-file "$out"/key --json | jq -r .publicKey > "$out"/pubkey
      mycelium inspect --key-file "$out"/key --json | jq -r .address > "$out"/ip
    '';
  };

}
