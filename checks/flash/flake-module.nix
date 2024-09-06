{ self, ... }:
{
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
        pkgs.age
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-install-machine.config.system.build.toplevel
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-install-machine.config.system.build.diskoScript
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-install-machine.config.system.build.diskoScript.drvPath
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-install-machine.config.system.clan.deployment.file
      ] ++ builtins.map (i: i.outPath) (builtins.attrValues self.inputs);
      closureInfo = pkgs.closureInfo { rootPaths = dependencies; };
    in
    {
      # Currently disabled...
      checks = pkgs.lib.mkIf (pkgs.stdenv.isLinux) {
        flash = (import ../lib/test-base.nix) {
          name = "flash";
          nodes.target = {
            virtualisation.emptyDiskImages = [ 4096 ];
            virtualisation.memorySize = 3000;
            environment.systemPackages = [
              self.packages.${pkgs.system}.clan-cli
            ] ++ self.packages.${pkgs.system}.clan-cli.runtimeDependencies;
            environment.variables."SOPS_AGE_KEY" = builtins.readFile ../lib/age/privkey;
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
            system.extraDependencies = dependencies;
          };
          testScript = ''
            start_all()

            machine.succeed("cp -r ${../..} test-flake && chmod -R +w test-flake")
            machine.succeed("clan secrets key generate")
            machine.succeed("clan secrets users add --debug --flake test-flake testuser '${builtins.readFile ../lib/age/pubkey}'")
            machine.succeed("clan flash --debug --flake test-flake --yes --disk main /dev/vdb test-install-machine")
          '';
        } { inherit pkgs self; };
      };
    };
}
