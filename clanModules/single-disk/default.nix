{ lib, config, ... }:
let
  cfg = config.clan.single-disk;
in
{
  options.clan.single-disk = {
    device = lib.mkOption {
      default = null;
      type = lib.types.nullOr lib.types.str;
      description = "The primary disk device to install the system on";
      # Question: should we set a default here?
      # default = "/dev/null";
    };
    suffix = lib.mkOption {
      default = config.clan.core.machine.diskId;
      defaultText = "abcdef";
      type = lib.types.nullOr lib.types.str;
      description = "The suffix to use for the disk";
    };
  };
  config = {
    assertions = [
      {
        assertion = cfg.suffix != null;
        message = "clan.core.machine.diskId must be set, please run `clan facts generate`";
      }
    ];
    boot.loader.grub.efiSupport = lib.mkDefault true;
    boot.loader.grub.efiInstallAsRemovable = lib.mkDefault true;
    disko.devices = lib.mkIf (cfg.suffix != null) {
      disk = {
        main = {
          type = "disk";
          # This is set through the UI
          device = cfg.device;

          content = {
            type = "gpt";
            partitions = {
              "boot-${cfg.suffix}" = {
                size = "1M";
                type = "EF02"; # for grub MBR
                priority = 1;
              };
              "ESP-${cfg.suffix}" = {
                size = "512M";
                type = "EF00";
                content = {
                  type = "filesystem";
                  format = "vfat";
                  mountpoint = "/boot";
                };
              };
              "root-${cfg.suffix}" = {
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
}
