(import ../lib/test-base.nix) (
  # Using nixos-test, because our own test system doesn't support the necessary
  # features for systemd.
  { lib, ... }:
  {
    name = "syncthing";

    nodes.introducer =
      { self, ... }:
      {
        imports = [
          self.clanModules.syncthing
          self.nixosModules.clanCore
          {
            clan.core.machineName = "introducer";
            clan.core.clanDir = ./.;
            environment.etc = {
              "syncthing.pam".source = ./introducer/introducer_test_cert;
              "syncthing.key".source = ./introducer/introducer_test_key;
              "syncthing.api".source = ./introducer/introducer_test_api;
            };
            clan.core.facts.services.syncthing.secret."syncthing.api".path = "/etc/syncthing.api";
            services.syncthing.cert = "/etc/syncthing.pam";
            services.syncthing.key = "/etc/syncthing.key";
            # Doesn't test zerotier!
            services.syncthing.openDefaultPorts = true;
            services.syncthing.settings.folders = {
              "Shared" = {
                enable = true;
                path = "~/Shared";
                versioning = {
                  type = "trashcan";
                  params = {
                    cleanoutDays = "30";
                  };
                };
              };
            };
            clan.syncthing.autoAcceptDevices = true;
            clan.syncthing.autoShares = [ "Shared" ];
            # For faster Tests
            systemd.timers.syncthing-auto-accept.timerConfig = {
              OnActiveSec = 1;
              OnUnitActiveSec = 1;
            };
          }
        ];
      };
    nodes.peer1 =
      { self, ... }:
      {
        imports = [
          self.clanModules.syncthing
          self.nixosModules.clanCore
          {
            clan.core.machineName = "peer1";
            clan.core.clanDir = ./.;
            clan.syncthing.introducer = lib.strings.removeSuffix "\n" (
              builtins.readFile ./introducer/introducer_device_id
            );
            environment.etc = {
              "syncthing.pam".source = ./peer_1/peer_1_test_cert;
              "syncthing.key".source = ./peer_1/peer_1_test_key;
            };
            services.syncthing.openDefaultPorts = true;
            services.syncthing.cert = "/etc/syncthing.pam";
            services.syncthing.key = "/etc/syncthing.key";
          }
        ];
      };
    nodes.peer2 =
      { self, ... }:
      {
        imports = [
          self.clanModules.syncthing
          self.nixosModules.clanCore
          {
            clan.core.machineName = "peer2";
            clan.core.clanDir = ./.;
            clan.syncthing.introducer = lib.strings.removeSuffix "\n" (
              builtins.readFile ./introducer/introducer_device_id
            );
            environment.etc = {
              "syncthing.pam".source = ./peer_2/peer_2_test_cert;
              "syncthing.key".source = ./peer_2/peer_2_test_key;
            };
            services.syncthing.openDefaultPorts = true;
            services.syncthing.cert = "/etc/syncthing.pam";
            services.syncthing.key = "/etc/syncthing.key";
          }
        ];
      };
    testScript = ''
      start_all()
      introducer.wait_for_unit("syncthing")
      peer1.wait_for_unit("syncthing")
      peer2.wait_for_unit("syncthing")
      peer1.wait_for_file("/home/user/Shared")
      peer2.wait_for_file("/home/user/Shared")
      introducer.shutdown()
      peer1.execute("echo hello > /home/user/Shared/hello")
      peer2.wait_for_file("/home/user/Shared/hello")
      out = peer2.succeed("cat /home/user/Shared/hello")
      print(out)
      assert "hello" in out
    '';
  }
)
