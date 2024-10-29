{
  pkgs,
  lib,
  config,
  ...
}:
{
  environment.systemPackages =
    [
      # essential debugging tools for networked services
      pkgs.dnsutils
      pkgs.tcpdump
      pkgs.curl
      pkgs.jq
      pkgs.htop

      pkgs.nixos-facter # for `clan machines update-hardware-config --backend nixos-facter`
    ]
    ++ lib.optional (lib.versionAtLeast config.nix.package.version "2.24")
      # needed to deploy via `clan machines update` if the flake has a git input
      # newer version of nix do have `libgit2`
      pkgs.gitMinimal;
}
