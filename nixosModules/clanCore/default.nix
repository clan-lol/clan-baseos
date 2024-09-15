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
  # Work around for https://github.com/NixOS/nixpkgs/issues/124215
  documentation.info.enable = lib.mkDefault false;
}
