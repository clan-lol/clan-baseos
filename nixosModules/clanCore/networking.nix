{ config, lib, ... }:
{
  options.clan.core = {
    networking = {
      targetHost = lib.mkOption {
        description = ''
          The target SSH node for deployment.

          By default, the node's attribute name will be used.
          If set to null, only local deployment will be supported.

          format: user@host:port&SSH_OPTION=SSH_VALUE
          examples:
            - machine.example.com
            - user@machine2.example.com
            - root@example.com:2222&IdentityFile=/path/to/private/key
        '';
        default = null;
        type = lib.types.nullOr lib.types.str;
      };
      buildHost = lib.mkOption {
        description = ''
          The build SSH node where nixos-rebuild will be executed.

          If set to null, the targetHost will be used.

          format: user@host:port&SSH_OPTION=SSH_VALUE
          examples:
            - machine.example.com
            - user@machine2.example.com
            - root@example.com:2222&IdentityFile=/path/to/private/key
        '';
        type = lib.types.nullOr lib.types.str;
        default = null;
      };
    };

    deployment = {
      requireExplicitUpdate = lib.mkOption {
        description = ''
          Do not update this machine when running `clan machines update` without any machines specified.

          This is useful for machines that are not always online or are not part of the regular update cycle.
        '';
        type = lib.types.bool;
        default = false;
      };
    };
  };

  imports = [
    # TODO: use mkRenamedOptionModule once this is fixed: https://github.com/NixOS/nixpkgs/issues/324802
    (lib.doRename rec {
      from = [
        "clan"
        "networking"
      ];
      to = [
        "clan"
        "core"
        "networking"
      ];
      visible = false;
      warn = true;
      use = lib.trace "Obsolete option `${lib.showOption from}' is used. It was renamed to `${lib.showOption to}'.";
      withPriority = false;
    })
    (lib.mkRenamedOptionModule
      [
        "clan"
        "deployment"
      ]
      [
        "clan"
        "core"
        "deployment"
      ]
    )
    (lib.mkRenamedOptionModule
      [
        "clan"
        "core"
        "networking"
        "deploymentAddress"
      ]
      [
        "clan"
        "core"
        "networking"
        "targetHost"
      ]
    )
  ];
  config = lib.mkIf config.clan.core.setDefaults {
    # conflicts with systemd-resolved
    networking.useHostResolvConf = false;

    # Allow PMTU / DHCP
    networking.firewall.allowPing = true;

    # The notion of "online" is a broken concept
    # https://github.com/systemd/systemd/blob/e1b45a756f71deac8c1aa9a008bd0dab47f64777/NEWS#L13
    systemd.services.NetworkManager-wait-online.enable = false;
    systemd.network.wait-online.enable = false;

    systemd.network.networks."99-ethernet-default-dhcp".networkConfig.MulticastDNS = lib.mkDefault true;
    systemd.network.networks."99-wireless-client-dhcp".networkConfig.MulticastDNS = lib.mkDefault true;
    networking.firewall.allowedUDPPorts = [ 5353 ]; # Multicast DNS

    # Use networkd instead of the pile of shell scripts
    networking.useNetworkd = lib.mkDefault true;
  };
}
