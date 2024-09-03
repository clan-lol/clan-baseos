{
  lib,
  pkgs,
  config,
  ...
}:
{
  # If we also need zfs, we can use the unstable version as we otherwise don't have a new enough kernel version
  boot.zfs.package = pkgs.zfsUnstable;
  boot.kernelPackages = lib.mkIf config.boot.zfs.enabled (
    lib.mkForce config.boot.zfs.package.latestCompatibleLinuxPackages
  );

  # Enable bcachefs support
  boot.supportedFilesystems.bcachefs = lib.mkDefault true;
}
