{
  lib,
  pkgs,
  config,
  ...
}:

let
  cfg = config.clan.iwd;
  toBase64 = (pkgs.callPackage ./base64.nix { inherit lib; }).toBase64;
  wifi_config = password: ''
    [Security]
      Passphrase=${password}
  '';
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
                type = lib.types.strMatching "^[a-zA-Z0-9._-]+$";
                default = name;
                description = "The name of the wifi network";
              };
              password = lib.mkOption {
                type = lib.types.str;
                description = "The password of the wifi network";
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
      # Systemd tmpfiles rule to create /var/lib/iwd/example.psk file
      systemd.tmpfiles.rules = lib.mapAttrsToList (
        _: value:
        "f+~ /var/lib/iwd/${value.ssid}.psk 0600 root root - ${toBase64 (wifi_config value.password)}"
      ) cfg.networks;

    })
    {
      # disable wpa supplicant
      networking.wireless.enable = false;

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
