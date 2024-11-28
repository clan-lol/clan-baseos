{ lib, config, ... }:

let
  cfg = config.clan.wifi;
  secret_path = ssid: config.clan.core.vars.generators."iwd.${ssid}".files.password.path;
  secret_generator = name: value: {
    name = "iwd.${value.ssid}";
    value = {
      script = ''
        config="
        [Settings]
          AutoConnect=${if value.AutoConnect then "true" else "false"}
        [Security]
          Passphrase=$(cat $prompts/password)
        "
        echo "$config" > $out/password
      '';
      prompts.password.type = "hidden";
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
          { name, ... }:
          {
            options = {
              ssid = lib.mkOption {
                type = lib.types.str;
                default = name;
                description = "The name of the wifi network";
              };
              AutoConnect = lib.mkOption {
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
      # Systemd tmpfiles rule to create /var/lib/iwd/example.pswd.${ssid}k file
      systemd.tmpfiles.rules = lib.mapAttrsToList (
        _: value: ''C "/var/lib/iwd/${value.ssid}.psk" 0600 root root - ${secret_path value.ssid}''
      ) cfg.networks;

      clan.core.vars.generators = lib.mapAttrs' secret_generator cfg.networks;

      systemd.services.iwd.partOf = [ "nixos-activation.service" ];
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
          Settings.AutoConnect = true;
        };
      };
    }
  ];
}
