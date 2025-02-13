{
  self,
  ...
}:
{
  clan.machines.test-morph-machine = {
    imports = [
      ./template/configuration.nix
      self.nixosModules.clanCore
    ];
    nixpkgs.hostPlatform = "x86_64-linux";
    environment.etc."testfile".text = "morphed";
  };

  clan.templates.machine.test-morph-template = {
    description = "Morph a machine";
    path = ./template;
  };

  perSystem =
    {
      pkgs,
      ...
    }:
    {
      checks = pkgs.lib.mkIf (pkgs.stdenv.isLinux && pkgs.stdenv.hostPlatform.system != "aarch64-linux") {
        test-morph = (import ../lib/test-base.nix) {
          name = "morph";

          nodes = {
            actual =
              { pkgs, ... }:
              let
                dependencies = [
                  self
                  pkgs.nixos-anywhere
                  pkgs.stdenv.drvPath
                  pkgs.stdenvNoCC
                  self.nixosConfigurations.test-morph-machine.config.system.build.toplevel
                  self.nixosConfigurations.test-morph-machine.config.system.clan.deployment.file
                ] ++ builtins.map (i: i.outPath) (builtins.attrValues self.inputs);
                closureInfo = pkgs.closureInfo { rootPaths = dependencies; };
              in

              {
                environment.etc."install-closure".source = "${closureInfo}/store-paths";
                system.extraDependencies = dependencies;
                virtualisation.memorySize = 1024;
                environment.systemPackages = [ self.packages.${pkgs.system}.clan-cli ];
              };
          };
          testScript = ''
            start_all()
            actual.fail("cat /etc/testfile")
            actual.succeed("env CLAN_DIR=${self} clan machines morph test-morph-template --i-will-be-fired-for-using-this --debug --name test-morph-machine")
            assert actual.succeed("cat /etc/testfile") == "morphed"
          '';
        } { inherit pkgs self; };
      };

    };
}
