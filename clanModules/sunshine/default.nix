{
  pkgs,
  config,
  lib,
  ...
}:
let
  ms-accept = pkgs.callPackage ../pkgs/moonlight-sunshine-accept { };
  sunshineConfiguration = pkgs.writeText "sunshine.conf" ''
    address_family = both
    channels = 5
    pkey = /var/lib/sunshine/sunshine.key
    cert = /var/lib/sunshine/sunshine.cert
    file_state = /var/lib/sunshine/state.json
    credentials_file = /var/lib/sunshine/credentials.json
  '';
  listenPort = 48011;
in
{
  networking.firewall = {
    allowedTCPPorts = [
      47984
      47989
      47990
      48010
      48011
    ];

    allowedUDPPorts = [
      47998
      47999
      48000
      48002
      48010
    ];
  };

  networking.firewall.allowedTCPPortRanges = [
    {
      from = 47984;
      to = 48010;
    }
  ];
  networking.firewall.allowedUDPPortRanges = [
    {
      from = 47998;
      to = 48010;
    }
  ];
  networking.firewall.interfaces."zt+".allowedTCPPorts = [
    47984
    47989
    47990
    48010
    listenPort
  ];
  networking.firewall.interfaces."zt+".allowedUDPPortRanges = [
    {
      from = 47998;
      to = 48010;
    }
  ];

  environment.systemPackages = [
    ms-accept
    pkgs.sunshine
    pkgs.avahi
    # Convenience script, until we find a better UX
    (pkgs.writers.writeDashBin "sun" ''
      ${pkgs.sunshine}/bin/sunshine -0 ${sunshineConfiguration} "$@"
    '')
    # Create a dummy account, for easier setup,
    # don't use this account in actual production yet.
    (pkgs.writers.writeDashBin "init-sun" ''
      ${pkgs.sunshine}/bin/sunshine \
      --creds "sunshine" "sunshine"
    '')
  ];

  # Required to simulate input
  boot.kernelModules = [ "uinput" ];

  services.udev.extraRules = ''
    KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess"
  '';

  security = {
    rtkit.enable = true;
    wrappers.sunshine = {
      owner = "root";
      group = "root";
      capabilities = "cap_sys_admin+p";
      source = "${pkgs.sunshine}/bin/sunshine";
    };
  };

  systemd.tmpfiles.rules = [
    "d '/var/lib/sunshine' 0770 'user' 'users' - -"
    "C '/var/lib/sunshine/sunshine.cert' 0644 'user' 'users' - ${
      config.clan.core.facts.services.sunshine.secret."sunshine.cert".path or ""
    }"
    "C '/var/lib/sunshine/sunshine.key' 0644 'user' 'users' - ${
      config.clan.core.facts.services.sunshine.secret."sunshine.key".path or ""
    }"
  ];

  hardware.graphics.enable = true;

  systemd.user.services.sunshine = {
    enable = true;
    description = "Sunshine self-hosted game stream host for Moonlight";
    startLimitBurst = 5;
    startLimitIntervalSec = 500;
    script = "/run/current-system/sw/bin/env /run/wrappers/bin/sunshine ${sunshineConfiguration}";
    serviceConfig = {
      Restart = "on-failure";
      RestartSec = "5s";
      ReadWritePaths = [ "/var/lib/sunshine" ];
      ReadOnlyPaths = [
        (config.clan.core.facts.services.sunshine.secret."sunshine.key".path or "")
        (config.clan.core.facts.services.sunshine.secret."sunshine.cert".path or "")
      ];
    };
    wantedBy = [ "graphical-session.target" ];
    partOf = [ "graphical-session.target" ];
    wants = [ "graphical-session.target" ];
    after = [
      "sunshine-init-state.service"
      "sunshine-init-credentials.service"
    ];
  };

  systemd.user.services.sunshine-init-state = {
    enable = true;
    description = "Sunshine self-hosted game stream host for Moonlight";
    startLimitBurst = 5;
    startLimitIntervalSec = 500;
    script = ''
      ${ms-accept}/bin/moonlight-sunshine-accept sunshine init-state --uuid ${
        config.clan.core.facts.services.sunshine.public.sunshine-uuid.value or null
      } --state-file /var/lib/sunshine/state.json
    '';
    serviceConfig = {
      Restart = "on-failure";
      RestartSec = "5s";
      Type = "oneshot";
      ReadWritePaths = [ "/var/lib/sunshine" ];
    };
    wantedBy = [ "graphical-session.target" ];
  };

  systemd.user.services.sunshine-init-credentials = {
    enable = true;
    description = "Sunshine self-hosted game stream host for Moonlight";
    startLimitBurst = 5;
    startLimitIntervalSec = 500;
    script = ''
      ${lib.getExe pkgs.sunshine} ${sunshineConfiguration} --creds sunshine sunshine
    '';
    serviceConfig = {
      Restart = "on-failure";
      RestartSec = "5s";
      Type = "oneshot";
      ReadWritePaths = [ "/var/lib/sunshine" ];
    };
    wantedBy = [ "graphical-session.target" ];
  };

  systemd.user.services.sunshine-listener = {
    enable = true;
    description = "Sunshine self-hosted game stream host for Moonlight";
    startLimitBurst = 5;
    startLimitIntervalSec = 500;
    script = ''
      ${ms-accept}/bin/moonlight-sunshine-accept sunshine listen --port ${builtins.toString listenPort} --uuid ${
        config.clan.core.facts.services.sunshine.public.sunshine-uuid.value or null
      }  --state /var/lib/sunshine/state.json --cert '${
        config.clan.core.facts.services.sunshine.public."sunshine.cert".value or null
      }'
    '';
    serviceConfig = {
      # );
      Restart = "on-failure";
      RestartSec = 5;
      ReadWritePaths = [ "/var/lib/sunshine" ];
    };
    wantedBy = [ "graphical-session.target" ];
  };

  clan.core.facts.services.ergochat = {
    secret."sunshine.key" = { };
    secret."sunshine.cert" = { };
    public."sunshine-uuid" = { };
    public."sunshine.cert" = { };
    generator.path = [
      pkgs.coreutils
      ms-accept
    ];
    generator.script = ''
      moonlight-sunshine-accept sunshine init
      mv credentials/cakey.pem "$secrets"/sunshine.key
      cp credentials/cacert.pem "$secrets"/sunshine.cert
      mv credentials/cacert.pem "$facts"/sunshine.cert
      mv uuid "$facts"/sunshine-uuid
    '';
  };
}
