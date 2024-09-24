{
  lib,
  pkgs,
  ...
}:
{
  # If we also need zfs, we can use the unstable version as we otherwise don't have a new enough kernel version
  boot.zfs.package = pkgs.zfsUnstable;

  # Enable bcachefs support
  boot.supportedFilesystems.bcachefs = lib.mkDefault true;
}
