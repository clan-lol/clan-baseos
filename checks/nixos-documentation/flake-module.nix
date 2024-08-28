{ self, ... }:
let
  documentationModule = {
    # This is how some downstream users currently generate documentation
    # If this breaks notify them via matrix since we spent ~5 hrs for bughunting last time.
    documentation.nixos.enable = true;
    documentation.nixos.extraModules = [
      self.nixosModules.clanCore
      { clan.core.clanDir = ./.; }
    ];
  };
in
{
  clan = {
    machines.test-documentation = {
      # Dummy file system
      fileSystems."/".device = "/dev/null";
      boot.loader.grub.device = "/dev/null";
      imports = [
        documentationModule
      ];
    };
  };
}
