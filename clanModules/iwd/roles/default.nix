{ lib, config, ... }:

let
  cfg = config.clan.iwd;
  secret_path = ssid: config.clan.core.facts.services."iwd.${ssid}".secret."iwd.${ssid}".path;
  secret_generator = name: value: {
    name = "iwd.${value.ssid}";
    value =
      let
        secret_name = "iwd.${value.ssid}";
      in
      {
        secret.${secret_name} = { };
        generator.prompt = "Wifi password for '${value.ssid}'";
        generator.script = ''
          config="
          [Security]
            Passphrase=$prompt_value
          "
          echo "$config" > $secrets/${secret_name}
        '';
      };
  };
in
{
  options.clan.iwd = {
    networks = lib.mkOption {
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
            };
          }
        )
      );
      default = { };
      description = "Wifi networks to predefine";
    };
  };

  imports = [
    (lib.mkRemovedOptionModule [
      "clan"
      "iwd"
      "enable"
    ] "Just define clan.iwd.networks to enable it")
  ];

  config = lib.mkMerge [
    (lib.mkIf (cfg.networks != { }) {
      # Systemd tmpfiles rule to create /var/lib/iwd/example.psk file
      systemd.tmpfiles.rules = lib.mapAttrsToList (
        _: value: "C /var/lib/iwd/${value.ssid}.psk 0600 root root - ${secret_path value.ssid}"
      ) cfg.networks;

      clan.core.facts.services = lib.mapAttrs' secret_generator cfg.networks;

      # TODO: restart the iwd.service if something changes
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
