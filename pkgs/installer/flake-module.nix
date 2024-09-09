{
  self,
  lib,
  ...
}:

let
  flashInstallerModule =
    { config, ... }:
    let
      suffix = config.clan.core.machine.diskId;
    in
    {
      imports = [
        ./iwd.nix
        self.nixosModules.installer
        self.clanModules.trusted-nix-caches
        self.clanModules.factless
      ];

      clan.factless = {
        diskId = "ac51e4623c804dcbbce0144ed8e16e55";
      };

      system.stateVersion = config.system.nixos.version;
      nixpkgs.pkgs = self.inputs.nixpkgs.legacyPackages.x86_64-linux;

      boot.loader.grub.efiSupport = lib.mkDefault true;
      boot.loader.grub.efiInstallAsRemovable = lib.mkDefault true;
      disko.devices = {
        disk = {
          "main" = {
            name = suffix;
            type = "disk";
            device = lib.mkDefault "/dev/null";
            content = {
              type = "gpt";
              partitions = {
                "boot" = {
                  size = "1M";
                  type = "EF02"; # for grub MBR
                  priority = 1;
                };
                "ESP" = {
                  size = "512M";
                  type = "EF00";
                  content = {
                    type = "filesystem";
                    format = "vfat";
                    mountpoint = "/boot";
                  };
                };
                "root" = {
                  size = "100%";
                  content = {
                    type = "filesystem";
                    format = "ext4";
                    mountpoint = "/";
                  };
                };
              };
            };
          };
        };
      };
    };

in
{
  clan = {
    # To directly flash the installer to a disk, use the following command:
    # $ clan flash flash-installer --disk main /dev/sdX --yes
    # This will include your ssh public keys in the installer.
    machines.flash-installer = {
      imports = [ flashInstallerModule ];
      boot.loader.grub.enable = lib.mkDefault true;
    };
  };
}
