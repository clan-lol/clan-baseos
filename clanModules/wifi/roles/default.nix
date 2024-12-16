{
  lib,
  config,
  pkgs,
  ...
}:

let
  cfg = config.clan.wifi;
  secret_path =
    network_name: config.clan.core.vars.generators."iwd.${network_name}".files.password.path;
  ssid_path = network_name: config.clan.core.vars.generators."iwd.${network_name}".files.ssid.path;
  secret_generator = name: value: {
    name = "iwd.${name}";
    value = {
      prompts.ssid.type = "line";
      prompts.ssid.createFile = true;
      prompts.password.type = "hidden";
      prompts.password.createFile = true;
      share = true;
    };
  };
in
{
  options.clan.wifi = {
    networks = lib.mkOption {
      visible = false;
      type = lib.types.attrsOf (
        lib.types.submodule (
          { ... }:
          {
            options = {
              enable = lib.mkOption {
                type = lib.types.bool;
                default = true;
                description = "Enable this wifi network";
              };
              autoConnect = lib.mkOption {
                type = lib.types.bool;
                default = true;
                description = "Automatically try to join this wifi network";
              };
            };
          }
        )
      );
      default = { };
      description = "Wifi networks to predefine";
    };
  };

  config = lib.mkMerge [
    (lib.mkIf (cfg.networks != { }) {

      clan.core.vars.generators = lib.mapAttrs' secret_generator cfg.networks;

      systemd.services.iwd.partOf = [ "nixos-activation.service" ];

      /*
        script that generates iwd config files inside /var/lib/iwd/clan and symlinks
          them to /var/lib/iwd.
      */
      systemd.services.iwd.serviceConfig.ExecStartPre = pkgs.writeShellScript "clan-iwd-setup" ''
        set -e

        rm -rf /var/lib/iwd/clan
        mkdir -p /var/lib/iwd/clan

        # remove all existing symlinks in /var/lib/iwd
        ${pkgs.findutils}/bin/find /var/lib/iwd -type l -exec rm {} \;

        ${toString (
          lib.mapAttrsToList (name: network: ''
            passwd=$(cat "${secret_path name}")
            ssid=$(cat "${ssid_path name}")
            echo "
            [Settings]
              autoConnect=${if network.autoConnect then "true" else "false"}
            [Security]
              Passphrase=$passwd
            " > "/var/lib/iwd/clan/$ssid.psk"
          '') cfg.networks
        )}

        # link all files in /var/lib/iwd/clan to /var/lib/iwd
        ${pkgs.findutils}/bin/find /var/lib/iwd/clan -type f -exec ln -s {} /var/lib/iwd \;
      '';
    })
    {
      # disable wpa supplicant
      networking.wireless.enable = false;

      # Set the network manager backend to iwd
      networking.networkmanager.wifi.backend = "iwd";

      # Use iwd instead of wpa_supplicant. It has a user friendly CLI
      networking.wireless.iwd = {
        enable = true;
        settings = {
          Network = {
            EnableIPv6 = true;
            RoutePriorityOffset = 300;
          };
          Settings.autoConnect = true;
        };
      };
    }
  ];
}
