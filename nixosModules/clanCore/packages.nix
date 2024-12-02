{
  pkgs,
  ...
}:
{
  environment.systemPackages = [
    # essential debugging tools for networked services
    pkgs.dnsutils
    pkgs.tcpdump
    pkgs.curl
    pkgs.jq
    pkgs.htop

    pkgs.nixos-facter # for `clan machines update-hardware-config --backend nixos-facter`

    pkgs.gitMinimal
  ];
}
