{
  config,
  ...
}:

{
  options.clan.installer =
    {
    };

  imports = [
    ../iwd
    ./bcachefs.nix
    ./zfs.nix
    ./hidden-ssh-announce.nix
    ../trusted-nix-caches
  ];

  config = {
    system.stateVersion = config.system.nixos.version;
  };
}
