{ config, lib, pkgs, ... }:
let
  cfg = config.clan.networking.zerotier;
  facts = config.clanCore.secrets.zerotier.facts or { };
  genMoonScript = pkgs.runCommand "genmoon" { nativeBuildInputs = [ pkgs.python3 ]; } ''
    install -Dm755 ${./genmoon.py} $out/bin/genmoon
    patchShebangs $out/bin/genmoon
  '';
  networkConfig = {
    authTokens = [
      null
    ];
    authorizationEndpoint = "";
    capabilities = [ ];
    clientId = "";
    dns = [ ];
    enableBroadcast = true;
    id = cfg.networkId;
    ipAssignmentPools = [ ];
    mtu = 2800;
    multicastLimit = 32;
    name = cfg.name;
    uwid = cfg.networkId;
    objtype = "network";
    private = !cfg.controller.public;
    remoteTraceLevel = 0;
    remoteTraceTarget = null;
    revision = 1;
    routes = [ ];
    rules = [
      {
        not = false;
        or = false;
        type = "ACTION_ACCEPT";
      }
    ];
    rulesSource = "";
    ssoEnabled = false;
    tags = [ ];
    v4AssignMode = {
      zt = false;
    };
    v6AssignMode = {
      "6plane" = false;
      rfc4193 = true;
      zt = false;
    };
  };
in
{
  options.clan.networking.zerotier = {
    networkId = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = ''
        zerotier networking id
      '';
    };
    name = lib.mkOption {
      type = lib.types.str;
      default = config.clanCore.clanName;
      description = ''
        zerotier network name
      '';
    };
    moon = {
      stableEndpoints = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = ''
          Make this machine a moon.
          Other machines can join this moon by adding this moon in their config.
          It will be reachable under the given stable endpoints.
        '';
      };
      orbitMoons = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = ''
          Join these moons.
          This machine will be able to reach all machines in these moons.
        '';
      };
    };
    subnet = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      readOnly = true;
      default =
        if cfg.networkId == null then
          null
        else
          let
            part0 = builtins.substring 0 2 cfg.networkId;
            part1 = builtins.substring 2 2 cfg.networkId;
            part2 = builtins.substring 4 2 cfg.networkId;
            part3 = builtins.substring 6 2 cfg.networkId;
            part4 = builtins.substring 8 2 cfg.networkId;
            part5 = builtins.substring 10 2 cfg.networkId;
            part6 = builtins.substring 12 2 cfg.networkId;
            part7 = builtins.substring 14 2 cfg.networkId;
          in
          "fd${part0}:${part1}${part2}:${part3}${part4}:${part5}${part6}:${part7}99:9300::/88";
      description = ''
        zerotier subnet
      '';
    };
    controller = {
      enable = lib.mkEnableOption "turn this machine into the networkcontroller";
      public = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = ''
          everyone can join a public network without having the administrator to accept
        '';
      };
    };
  };
  config = lib.mkMerge [
    ({
      # Override license so that we can build zerotierone without
      # having to re-import nixpkgs.
      services.zerotierone.package = lib.mkDefault (pkgs.zerotierone.overrideAttrs (_old: { meta = { }; }));
    })
    (lib.mkIf ((facts.zerotier-meshname.value or null) != null) {
      environment.etc."zerotier/hostname".text = "${facts.zerotier-meshname.value}.vpn";
    })
    (lib.mkIf ((facts.zerotier-ip.value or null) != null) {
      environment.etc."zerotier/ip".text = facts.zerotier-ip.value;
    })
    (lib.mkIf (cfg.networkId != null) {
      clan.networking.meshnamed.networks.vpn.subnet = cfg.subnet;

      systemd.network.networks."09-zerotier" = {
        matchConfig.Name = "zt*";
        networkConfig = {
          LLMNR = true;
          LLDP = true;
          MulticastDNS = true;
          KeepConfiguration = "static";
        };
      };

      systemd.services.zerotierone.serviceConfig.ExecStartPre = [
        "+${pkgs.writeShellScript "init-zerotier" ''
           cp ${config.clanCore.secrets.zerotier.secrets.zerotier-identity-secret.path} /var/lib/zerotier-one/identity.secret
           zerotier-idtool getpublic /var/lib/zerotier-one/identity.secret > /var/lib/zerotier-one/identity.public

           ${lib.optionalString (cfg.controller.enable) ''
             mkdir -p /var/lib/zerotier-one/controller.d/network
             ln -sfT ${pkgs.writeText "net.json" (builtins.toJSON networkConfig)} /var/lib/zerotier-one/controller.d/network/${cfg.networkId}.json
           ''}
           ${lib.optionalString (cfg.moon.stableEndpoints != []) ''
             if [[ ! -f /var/lib/zerotier-one/moon.json ]]; then
               zerotier-idtool initmoon /var/lib/zerotier-one/identity.public > /var/lib/zerotier-one/moon.json
             fi
             ${genMoonScript}/bin/genmoon /var/lib/zerotier-one/moon.json ${builtins.toFile "moon.json" (builtins.toJSON cfg.moon.stableEndpoints)} /var/lib/zerotier-one/moons.d
           ''}

           # cleanup old networks
           if [[ -d /var/lib/zerotier-one/networks.d ]]; then
             find /var/lib/zerotier-one/networks.d \
               -type f \
               -name "*.conf" \
               -not \( ${lib.concatMapStringsSep " -o " (netId: ''-name "${netId}.conf"'') config.services.zerotierone.joinNetworks} \) \
               -delete
           fi
         ''}"
      ];
      systemd.services.zerotierone.serviceConfig.ExecStartPost = [
        "+${pkgs.writeShellScript "configure-interface" ''
          while ! ${pkgs.netcat}/bin/nc -z localhost 9993; do
            sleep 0.1
          done
          zerotier-cli listnetworks -j | ${pkgs.jq}/bin/jq -r '.[] | [.portDeviceName, .name] | @tsv' \
            | while IFS=$'\t' read -r portDeviceName name; do
              if [[ -z "$name" ]] || [[ -z "$portDeviceName" ]]; then
                continue
              fi
              # Execute the command for each element
              ${pkgs.iproute2}/bin/ip link property add dev "$portDeviceName" altname "$name"
          done

          ${lib.concatMapStringsSep "\n" (moon: ''
            zerotier-cli orbit ${moon} ${moon}
          '') cfg.moon.orbitMoons}
         ''}"
      ];

      networking.firewall.interfaces."zt+".allowedTCPPorts = [ 5353 ]; # mdns
      networking.firewall.interfaces."zt+".allowedUDPPorts = [ 5353 ]; # mdns

      networking.firewall.allowedTCPPorts = [ 9993 ]; # zerotier
      networking.firewall.allowedUDPPorts = [ 9993 ]; # zerotier

      networking.networkmanager.unmanaged = [ "interface-name:zt*" ];

      services.zerotierone = {
        enable = true;
        joinNetworks = [ cfg.networkId ];
      };

      # The official zerotier tcp relay no longer works: https://github.com/zerotier/ZeroTierOne/issues/2202
      # So we host our own relay in https://git.clan.lol/clan/clan-infra
      services.zerotierone.localConf.settings.tcpFallbackRelay = "65.21.12.51/4443";
    })
    (lib.mkIf cfg.controller.enable {
      # only the controller needs to have the key in the repo, the other clients can be dynamic
      # we generate the zerotier code manually for the controller, since it's part of the bootstrap command
      clanCore.secrets.zerotier = {
        facts.zerotier-ip = { };
        facts.zerotier-meshname = { };
        facts.zerotier-network-id = { };
        secrets.zerotier-identity-secret = { };
        generator.path = [ config.services.zerotierone.package pkgs.fakeroot pkgs.python3 ];
        generator.script = ''
          python3 ${./generate.py} --mode network \
            --ip "$facts/zerotier-ip" \
            --meshname "$facts/zerotier-meshname" \
            --identity-secret "$secrets/zerotier-identity-secret" \
            --network-id "$facts/zerotier-network-id"
        '';
      };
      clanCore.state.zerotier.folders = [ "/var/lib/zerotier-one" ];

      environment.systemPackages = [ config.clanCore.clanPkgs.zerotier-members ];
    })
    (lib.mkIf (config.clanCore.secretsUploadDirectory != null && !cfg.controller.enable && cfg.networkId != null) {
      clanCore.secrets.zerotier = {
        facts.zerotier-ip = { };
        facts.zerotier-meshname = { };
        secrets.zerotier-identity-secret = { };
        generator.path = [ config.services.zerotierone.package pkgs.python3 ];
        generator.script = ''
          python3 ${./generate.py} --mode identity \
            --ip "$facts/zerotier-ip" \
            --meshname "$facts/zerotier-meshname" \
            --identity-secret "$secrets/zerotier-identity-secret" \
            --network-id ${cfg.networkId}
        '';
      };
    })
    (lib.mkIf (cfg.controller.enable && (facts.zerotier-network-id.value or null) != null) {
      clan.networking.zerotier.networkId = facts.zerotier-network-id.value;
      environment.etc."zerotier/network-id".text = facts.zerotier-network-id.value;
      systemd.services.zerotierone.serviceConfig.ExecStartPost = [
        "+${pkgs.writeShellScript "whitelist-controller" ''
          ${config.clanCore.clanPkgs.zerotier-members}/bin/zerotier-members allow ${builtins.substring 0 10 cfg.networkId}
        ''}"
      ];
    })
  ];
}
