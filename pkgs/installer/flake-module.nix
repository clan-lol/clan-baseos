{ self, lib, ... }:

let

  flashInstallerModule =
    { config, ... }:
    {
      imports = [
        ./iwd.nix
        self.nixosModules.installer
        # Allow to download pre-build binaries from our nix caches
        self.clanModules.trusted-nix-caches
      ];

      system.stateVersion = config.system.nixos.version;
      nixpkgs.pkgs = self.inputs.nixpkgs.legacyPackages.x86_64-linux;
    }
    // flashDiskoConfig;

  # Important: The partition names need to be different to the clan install
  flashDiskoConfig = {
    boot.loader.grub.efiSupport = lib.mkDefault true;
    boot.loader.grub.efiInstallAsRemovable = lib.mkDefault true;
    disko.devices = {
      disk = {
        main = {
          type = "disk";
          device = lib.mkDefault "/dev/null";
          content = {
            type = "gpt";
            partitions = {
              installer-boot = {
                size = "1M";
                type = "EF02"; # for grub MBR
                priority = 1;
              };
              installer-ESP = {
                size = "512M";
                type = "EF00";
                content = {
                  type = "filesystem";
                  format = "vfat";
                  mountpoint = "/boot";
                };
              };
              installer-root = {
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
