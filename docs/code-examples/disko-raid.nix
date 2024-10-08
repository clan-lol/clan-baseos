{
  lib,
  config,
  clan-core,
  ...
}:
let
  suffix = config.clan.core.vars.generators.disk-id.files.diskId.value;
  mirrorBoot = idx: {
    # suffix is to prevent disk name collisions
    name = idx + suffix;
    type = "disk";
    device = "/dev/disk/by-id/${idx}";
    content = {
      type = "gpt";
      partitions = {
        "boot" = {
          size = "1M";
          type = "EF02"; # for grub MBR
          priority = 1;
        };
        "ESP" = lib.mkIf (idx == "nvme-eui.002538b931b59865") {
          size = "1G";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "nofail" ];
          };
        };
        "root" = {
          size = "100%";
          content = {
            type = "zfs";
            pool = "zroot";
          };
        };
      };
    };
  };
in
{
  imports = [
    clan-core.clanModules.disk-id
  ];

  config = {
    boot.loader.systemd-boot.enable = true;

    disko.devices = {
      disk = {
        x = mirrorBoot "nvme-eui.002538b931b59865";
        y = mirrorBoot "my-other-disk";
      };
      zpool = {
        zroot = {
          type = "zpool";
          rootFsOptions = {
            compression = "lz4";
            acltype = "posixacl";
            xattr = "sa";
            "com.sun:auto-snapshot" = "true";
            mountpoint = "none";
          };
          datasets = {
            "root" = {
              type = "zfs_fs";
              options = {
                mountpoint = "none";
                encryption = "aes-256-gcm";
                keyformat = "passphrase";
                keylocation = "file:///tmp/secret.key";
              };
            };
            "root/nixos" = {
              type = "zfs_fs";
              options.mountpoint = "/";
              mountpoint = "/";
            };
            "root/home" = {
              type = "zfs_fs";
              options.mountpoint = "/home";
              mountpoint = "/home";
            };
            "root/tmp" = {
              type = "zfs_fs";
              mountpoint = "/tmp";
              options = {
                mountpoint = "/tmp";
                sync = "disabled";
              };
            };
          };
        };
      };
    };
  };
}
