{ lib, config, ... }:
{
  imports = [
    ./backups.nix
    ./facts
    ./imports.nix
    ./inventory/interface.nix
    ./manual.nix
    ./meta/interface.nix
    ./metadata.nix
    ./networking.nix
    ./nix-settings.nix
    ./options.nix
    ./outputs.nix
    ./packages.nix
    ./schema.nix
    ./sops.nix
    ./vars
    ./vm.nix
    ./wayland-proxy-virtwl.nix
    ./zerotier
    ./zfs.nix
  ];

  # Use systemd during boot as well except:
  # - systems with raids as this currently require manual configuration: https://github.com/NixOS/nixpkgs/issues/210210
  # - for containers we currently rely on the `stage-2` init script that sets up our /etc
  boot.initrd.systemd.enable = lib.mkDefault (!config.boot.swraid.enable && !config.boot.isContainer);

  # Work around for https://github.com/NixOS/nixpkgs/issues/124215
  documentation.info.enable = lib.mkDefault false;

  # Don't install the /lib/ld-linux.so.2 stub. This saves one instance of nixpkgs.
  environment.ldso32 = null;
}
