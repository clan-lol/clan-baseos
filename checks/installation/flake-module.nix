{
  self,
  inputs,
  lib,
  ...
}:
{
  clan.machines.test-install-machine = {
    clan.core.networking.targetHost = "test-install-machine";
    fileSystems."/".device = lib.mkDefault "/dev/vda";
    boot.loader.grub.device = lib.mkDefault "/dev/vda";

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
          ../lib/minify.nix
        ];
        clan.single-disk.device = "/dev/vda";

        environment.etc."install-successful".text = "ok";

        nixpkgs.hostPlatform = "x86_64-linux";
        boot.consoleLogLevel = lib.mkForce 100;
        boot.kernelParams = [ "boot.shell_on_fail" ];
      };
  };
  perSystem =
    {
      pkgs,
      lib,
      ...
    }:
    let
      dependencies = [
        self
        self.nixosConfigurations.test-install-machine.config.system.build.toplevel
        self.nixosConfigurations.test-install-machine.config.system.build.diskoScript
        self.nixosConfigurations.test-install-machine.config.system.clan.deployment.file
        pkgs.stdenv.drvPath
        pkgs.nixos-anywhere
      ] ++ builtins.map (i: i.outPath) (builtins.attrValues self.inputs);
      closureInfo = pkgs.closureInfo { rootPaths = dependencies; };
    in
    {
      # On aarch64-linux, hangs on reboot with after installation:
      # vm-test-run-test-installation> (finished: waiting for the VM to power off, in 1.97 seconds)
      # vm-test-run-test-installation>
      # vm-test-run-test-installation> new_machine: must succeed: cat /etc/install-successful
      # vm-test-run-test-installation> new_machine: waiting for the VM to finish booting
      # vm-test-run-test-installation> new_machine: starting vm
      # vm-test-run-test-installation> new_machine: QEMU running (pid 80)
      # vm-test-run-test-installation> new_machine: Guest root shell did not produce any data yet...
      # vm-test-run-test-installation> new_machine:   To debug, enter the VM and run 'systemctl status backdoor.service'.
      checks = pkgs.lib.mkIf (pkgs.stdenv.isLinux && pkgs.stdenv.hostPlatform.system != "aarch64-linux") {
        test-installation = (import ../lib/test-base.nix) {
          name = "test-installation";
          nodes.target = {
            services.openssh.enable = true;
            virtualisation.diskImage = "./target.qcow2";
            virtualisation.useBootLoader = true;

            # virtualisation.fileSystems."/" = {
            #   device = "/dev/disk/by-label/this-is-not-real-and-will-never-be-used";
            #   fsType = "ext4";
            # };
          };
          nodes.installer =
            { modulesPath, ... }:
            {
              imports = [
                (modulesPath + "/../tests/common/auto-format-root-device.nix")
              ];
              services.openssh.enable = true;
              users.users.root.openssh.authorizedKeys.keyFiles = [ ../lib/ssh/pubkey ];
              system.nixos.variant_id = "installer";
              environment.systemPackages = [ pkgs.nixos-facter ];
              virtualisation.emptyDiskImages = [ 512 ];
              virtualisation.diskSize = 8 * 1024;
              virtualisation.rootDevice = "/dev/vdb";
              # both installer and target need to use the same diskImage
              virtualisation.diskImage = "./target.qcow2";
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
          nodes.client = {
            environment.systemPackages = [
              self.packages.${pkgs.system}.clan-cli
            ] ++ self.packages.${pkgs.system}.clan-cli.runtimeDependencies;
            environment.etc."install-closure".source = "${closureInfo}/store-paths";
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
            client.start()
            installer.start()

            client.succeed("${pkgs.coreutils}/bin/install -Dm 600 ${../lib/ssh/privkey} /root/.ssh/id_ed25519")
            client.wait_until_succeeds("timeout 2 ssh -o StrictHostKeyChecking=accept-new -v root@installer hostname")
            client.succeed("cp -r ${../..} test-flake && chmod -R +w test-flake")
            client.fail("test -f test-flake/machines/test-install-machine/hardware-configuration.nix")
            client.succeed("clan machines update-hardware-config --flake test-flake test-install-machine root@installer >&2")
            client.succeed("test -f test-flake/machines/test-install-machine/hardware-configuration.nix")
            client.succeed("clan machines update-hardware-config --backend nixos-facter --flake test-flake test-install-machine root@installer>&2")
            client.succeed("test -f test-flake/machines/test-install-machine/facter.json")
            client.succeed("clan machines install --debug --flake ${../..} --yes test-install-machine --target-host root@installer >&2")
            try:
              installer.shutdown()
            except BrokenPipeError:
              # qemu has already exited
              pass

            target.state_dir = installer.state_dir
            target.start()
            target.wait_for_unit("multi-user.target")
            assert(target.succeed("cat /etc/install-successful").strip() == "ok")
          '';
        } { inherit pkgs self; };
      };
    };
}
