{ inputs, self, ... }:
{
  flake.nixosModules = {
    hidden-ssh-announce.imports = [ ./hidden-ssh-announce.nix ];
    bcachefs.imports = [ ./bcachefs.nix ];
    zfs.imports = [ ./zfs.nix ];
    installer.imports = [
      ./installer
      self.nixosModules.hidden-ssh-announce
      self.nixosModules.bcachefs
      self.nixosModules.zfs
    ];
    clanCore.imports = [
      inputs.sops-nix.nixosModules.sops
      inputs.disko.nixosModules.default
      ./clanCore
      (
        { pkgs, lib, ... }:
        {
          clan.core.clanPkgs = lib.mkDefault self.packages.${pkgs.hostPlatform.system};
        }
      )
    ];
  };
}
