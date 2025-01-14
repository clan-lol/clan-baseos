{
  lib,
  pkgs,
  modulesPath,
  ...
}:

let
  network-status = pkgs.writeShellScriptBin "network-status" ''
    export PATH=${
      lib.makeBinPath (
        with pkgs;
        [
          iproute2
          coreutils
          gnugrep
          nettools
          gum
        ]
      )
    }
    set -efu -o pipefail
    msgs=()
    if [[ -e /var/shared/qrcode.utf8 ]]; then
      qrcode=$(gum style --border-foreground 240 --border normal "$(< /var/shared/qrcode.utf8)")
      msgs+=("$qrcode")
    fi
    network_status="Local network addresses:
    $(ip -brief -color addr | grep -v 127.0.0.1)
    $([[ -e /var/shared/onion-hostname ]] && echo "Onion address: $(cat /var/shared/onion-hostname)" || echo "Onion address: Waiting for tor network to be ready...")
    Multicast DNS: $(hostname).local"
    network_status=$(gum style --border-foreground 240 --border normal "$network_status")
    msgs+=("$network_status")
    msgs+=("Press 'Ctrl-C' for console access")

    gum join --vertical "''${msgs[@]}"
  '';
in
{
  ############################################
  #                                          #
  # For install image debugging execute:     #
  # $ qemu-kvm result/stick.raw -snapshot    #
  #                                          #
  ############################################
  imports = [
    (modulesPath + "/profiles/installation-device.nix")
    (modulesPath + "/profiles/all-hardware.nix")
    (modulesPath + "/profiles/base.nix")
    ./zfs-latest.nix
  ];

  environment.systemPackages = [
    pkgs.nixos-facter
    network-status
  ];

  nix.settings.extra-substituters = [ "/" ];

  ########################################################################################################
  #                                                                                                      #
  # Copied from:                                                                                         #
  # https://github.com/nix-community/nixos-images/blob/main/nix/image-installer/module.nix#L46C3-L117C6  #
  #                                                                                                      #
  ########################################################################################################
  systemd.tmpfiles.rules = [ "d /var/shared 0777 root root - -" ];
  services.openssh.settings.PermitRootLogin = lib.mkForce "prohibit-password";

  hidden-ssh-announce = {
    enable = true;
    script = pkgs.writeShellScript "write-hostname" ''
      set -efu
      export PATH=${
        lib.makeBinPath (
          with pkgs;
          [
            iproute2
            coreutils
            jq
            qrencode
          ]
        )
      }

      mkdir -p /var/shared
      echo "$1" > /var/shared/onion-hostname
      local_addrs=$(ip -json addr | jq '[map(.addr_info) | flatten | .[] | select(.scope == "global") | .local]')
      jq -nc \
        --arg onion_address "$(cat /var/shared/onion-hostname)" \
        --argjson local_addrs "$local_addrs" \
        '{ pass: null, tor: $onion_address, addrs: $local_addrs }' \
        > /var/shared/login.json
      cat /var/shared/login.json | qrencode -s 2 -m 2 -t utf8 -o /var/shared/qrcode.utf8
    '';
  };

  services.getty.autologinUser = lib.mkForce "root";

  console.earlySetup = true;
  console.font = lib.mkDefault "${pkgs.terminus_font}/share/consolefonts/ter-u22n.psf.gz";

  # Less ipv6 addresses to reduce the noise
  networking.tempAddresses = "disabled";

  # Tango theme: https://yayachiken.net/en/posts/tango-colors-in-terminal/
  console.colors = lib.mkDefault [
    "000000"
    "CC0000"
    "4E9A06"
    "C4A000"
    "3465A4"
    "75507B"
    "06989A"
    "D3D7CF"
    "555753"
    "EF2929"
    "8AE234"
    "FCE94F"
    "739FCF"
    "AD7FA8"
    "34E2E2"
    "EEEEEC"
  ];

  programs.bash.interactiveShellInit = ''
    if [[ "$(tty)" =~ /dev/(tty1|hvc0|ttyS0)$ ]]; then
      # workaround for https://github.com/NixOS/nixpkgs/issues/219239
      systemctl restart systemd-vconsole-setup.service

      watch --no-title --color ${network-status}/bin/network-status
    fi
  '';
}
