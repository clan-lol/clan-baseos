{ ... }:
{
  flake.clanModules = {
    borgbackup = ./borgbackup;
    borgbackup-static = ./borgbackup-static;
    deltachat = ./deltachat;
    dyndns = ./dyndns;
    ergochat = ./ergochat;
    garage = ./garage;
    golem-provider = ./golem-provider;
    heisenbridge = ./heisenbridge;
    iwd = ./iwd;
    localbackup = ./localbackup;
    localsend = ./localsend;
    matrix-synapse = ./matrix-synapse;
    moonlight = ./moonlight;
    mumble = ./mumble;
    packages = ./packages;
    nginx = ./nginx;
    postgresql = ./postgresql;
    root-password = ./root-password;
    single-disk = ./single-disk;
    sshd = ./sshd;
    static-hosts = ./static-hosts;
    sunshine = ./sunshine;
    syncthing = ./syncthing;
    syncthing-static-peers = ./syncthing-static-peers;
    thelounge = ./thelounge;
    trusted-nix-caches = ./trusted-nix-caches;
    user-password = ./user-password;
    vaultwarden = ./vaultwarden;
    xfce = ./xfce;
    zerotier-static-peers = ./zerotier-static-peers;
    zt-tcp-relay = ./zt-tcp-relay;
  };
}
