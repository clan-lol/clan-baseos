{ self, lib, ... }:

{
  clan.machines.test-install-machine = {
    clan.core.networking.targetHost = "test-install-machine";
    clan.core.machine = {
      id = "a73f5245cdba4576ab6cfef3145ac9ec";
      diskId = "c4c47b";
    };
    fileSystems."/".device = lib.mkDefault "/dev/vdb";
    boot.loader.grub.device = lib.mkDefault "/dev/vdb";

    imports = [ self.nixosModules.test-install-machine ];
  };
  flake.nixosModules = {
    test-install-machine =
      { lib, modulesPath, ... }:
      {
        imports = [
          self.clanModules.single-disk
          (modulesPath + "/testing/test-instrumentation.nix") # we need these 2 modules always to be able to run the tests
          (modulesPath + "/profiles/qemu-guest.nix")
        ];
        clan.single-disk.device = "/dev/vdb";
        clan.core.machine = {
          id = "a73f5245cdba4576ab6cfef3145ac9ec";
          diskId = "c4c47b";
        };
        environment.etc."install-successful".text = "ok";

        boot.consoleLogLevel = lib.mkForce 100;
        boot.kernelParams = [ "boot.shell_on_fail" ];
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
        self
        pkgs.age
        self.nixosConfigurations.test-install-machine.config.system.build.toplevel
        self.nixosConfigurations.test-install-machine.config.system.build.diskoScript
        self.clanInternals.machines.${pkgs.hostPlatform.system}.test-install-machine.config.system.build.diskoScript.drvPath
        self.nixosConfigurations.test-install-machine.config.system.clan.deployment.file
        pkgs.stdenv.drvPath
        pkgs.nixos-anywhere
      ] ++ builtins.map (i: i.outPath) (builtins.attrValues self.inputs);
      closureInfo = pkgs.closureInfo { rootPaths = dependencies; };
    in
    {
      checks = pkgs.lib.mkIf (pkgs.stdenv.isLinux) {
        test-installation = (import ../lib/test-base.nix) {
          name = "test-installation";
          nodes.target = {
            services.openssh.enable = true;
            users.users.root.openssh.authorizedKeys.keyFiles = [ ../lib/ssh/pubkey ];
            system.nixos.variant_id = "installer";

            virtualisation.emptyDiskImages = [ 4096 ];
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
          nodes.client = {
            environment.systemPackages = [
              self.packages.${pkgs.system}.clan-cli
            ] ++ self.packages.${pkgs.system}.clan-cli.runtimeDependencies;
            environment.etc."install-closure".source = "${closureInfo}/store-paths";
            environment.variables."SOPS_AGE_KEY" = builtins.readFile ../lib/age/privkey;
            virtualisation.memorySize = 2048;
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
            def create_test_machine(oldmachine=None, args={}): # taken from <nixpkgs/nixos/tests/installer.nix>
                startCommand = "${pkgs.qemu_test}/bin/qemu-kvm"
                startCommand += " -cpu max -m 1024 -virtfs local,path=/nix/store,security_model=none,mount_tag=nix-store"
                startCommand += f' -drive file={oldmachine.state_dir}/empty0.qcow2,id=drive1,if=none,index=1,werror=report'
                startCommand += ' -device virtio-blk-pci,drive=drive1'
                machine = create_machine({
                  "startCommand": startCommand,
                } | args)
                driver.machines.append(machine)
                return machine

            start_all()

            client.succeed("${pkgs.coreutils}/bin/install -Dm 600 ${../lib/ssh/privkey} /root/.ssh/id_ed25519")
            client.wait_until_succeeds("timeout 2 ssh -o StrictHostKeyChecking=accept-new -v root@target hostname")
            client.succeed("cp -r ${../..} test-flake && chmod -R +w test-flake")
            client.fail("test -f test-flake/machines/test-install-machine/hardware-configuration.nix")
            client.succeed("clan secrets key generate")
            client.succeed("clan secrets users add --debug --flake test-flake testuser '${builtins.readFile ../lib/age/pubkey}'")
            client.succeed("clan machines hw-generate --debug --flake test-flake test-install-machine root@target>&2")
            client.succeed("test -f test-flake/machines/test-install-machine/hardware-configuration.nix")
            client.succeed("clan machines install --debug --flake test-flake --yes test-install-machine root@target >&2")
            try:
              target.shutdown()
            except BrokenPipeError:
              # qemu has already exited
              pass

            new_machine = create_test_machine(oldmachine=target, args={ "name": "new_machine" })
            assert(new_machine.succeed("cat /etc/install-successful").strip() == "ok")
          '';
        } { inherit pkgs self; };
      };
    };
}
