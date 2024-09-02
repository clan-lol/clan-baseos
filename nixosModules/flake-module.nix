{ inputs, self, ... }:
{
  flake.nixosModules = {
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
