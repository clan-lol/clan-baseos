{ self, lib, ... }:
{
  clan.machines.test-flash-machine = {
    clan.core.networking.targetHost = "test-flash-machine";
    fileSystems."/".device = lib.mkDefault "/dev/vda";
    boot.loader.grub.device = lib.mkDefault "/dev/vda";

    imports = [ self.nixosModules.test-flash-machine ];
  };

  flake.nixosModules = {
    test-flash-machine =
      { lib, ... }:
      {
        imports = [ self.nixosModules.test-install-machine ];

        clan.core.vars.generators.test = lib.mkForce { };

        disko.devices.disk.main.preCreateHook = lib.mkForce "";
      };
  };

  perSystem =
    {
      nodes,
      pkgs,
      lib,
      ...
    }:
    let
      dependencies = [
        pkgs.disko
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-flash-machine.pkgs.perlPackages.ConfigIniFiles
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-flash-machine.pkgs.perlPackages.FileSlurp

        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-flash-machine.config.system.build.toplevel
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-flash-machine.config.system.build.diskoScript
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-flash-machine.config.system.build.diskoScript.drvPath
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-flash-machine.config.system.clan.deployment.file

      ] ++ builtins.map (i: i.outPath) (builtins.attrValues self.inputs);
      closureInfo = pkgs.closureInfo { rootPaths = dependencies; };
    in
    {
      checks = pkgs.lib.mkIf (pkgs.stdenv.isLinux) {
        flash = (import ../lib/test-base.nix) {
          name = "flash";
          nodes.target = {
            virtualisation.emptyDiskImages = [ 4096 ];
            virtualisation.memorySize = 3000;
            environment.systemPackages = [ self.packages.${pkgs.system}.clan-cli ];
            environment.etc."install-closure".source = "${closureInfo}/store-paths";

            nix.settings = {
              substituters = lib.mkForce [ ];
              hashed-mirrors = null;
              connect-timeout = lib.mkForce 3;
              flake-registry = pkgs.writeText "flake-registry" ''{"flakes":[],"version":2}'';
              experimental-features = [
                "nix-command"
                "flakes"
              ];
            };
          };
          testScript = ''
            start_all()

            machine.succeed("clan flash write --debug --flake ${../..} --yes --disk main /dev/vdb test-flash-machine")
          '';
        } { inherit pkgs self; };
      };
    };
}
