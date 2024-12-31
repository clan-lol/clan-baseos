(import ../lib/test-base.nix) (
  { ... }:
  let
    common =
      { self, pkgs, ... }:
      {
        imports = [
          self.clanModules.mumble
          {
            clan.services.mumble.user = "alice";
          }
          self.nixosModules.clanCore
          (self.inputs.nixpkgs + "/nixos/tests/common/x11.nix")
          {
            clan.core.settings.directory = ./.;
            environment.systemPackages = [ pkgs.killall ];
            clan.core.facts.services.mumble.secret."mumble-key".path = "/etc/mumble-key";
            clan.core.facts.services.mumble.public."mumble-cert".path = "/etc/mumble-cert";
          }
        ];

      };
  in
  {
    name = "mumble";

    enableOCR = true;

    nodes.peer1 =
      { ... }:
      {
        imports = [
          common
          {
            clan.core.machineName = "peer1";
            environment.etc = {
              "mumble-key".source = ./peer_1/peer_1_test_key;
              "mumble-cert".source = ./peer_1/peer_1_test_cert;
            };
            systemd.tmpfiles.settings."vmsecrets" = {
              "/var/lib/murmur/sslKey" = {
                C.argument = "${./peer_1/peer_1_test_key}";
                z = {
                  mode = "0400";
                  user = "murmur";
                };
              };
              "/var/lib/murmur/sslCert" = {
                C.argument = "${./peer_1/peer_1_test_cert}";
                z = {
                  mode = "0400";
                  user = "murmur";
                };
              };
            };
            clan.core.facts.services.mumble.secret."mumble-key".path = "/etc/mumble-key";
            clan.core.facts.services.mumble.public."mumble-cert".path = "/etc/mumble-cert";
          }
        ];
      };
    nodes.peer2 =
      { ... }:
      {
        imports = [
          common
          {
            clan.core.machineName = "peer2";
            environment.etc = {
              "mumble-key".source = ./peer_2/peer_2_test_key;
              "mumble-cert".source = ./peer_2/peer_2_test_cert;
            };
            systemd.tmpfiles.settings."vmsecrets" = {
              "/var/lib/murmur/sslKey" = {
                C.argument = "${./peer_2/peer_2_test_key}";
                z = {
                  mode = "0400";
                  user = "murmur";
                };
              };
              "/var/lib/murmur/sslCert" = {
                C.argument = "${./peer_2/peer_2_test_cert}";
                z = {
                  mode = "0400";
                  user = "murmur";
                };
              };
            };
          }
        ];
      };
    testScript = ''
      start_all()

      with subtest("Waiting for x"):
        peer1.wait_for_x()
        peer2.wait_for_x()

      with subtest("Waiting for murmur"):
        peer1.wait_for_unit("murmur.service")
        peer2.wait_for_unit("murmur.service")

      with subtest("Starting Mumble"):
        # starting mumble is blocking
        peer1.execute("mumble >&2 &")
        peer2.execute("mumble >&2 &")

      with subtest("Wait for Mumble"):
        peer1.wait_for_window(r"^Mumble$")
        peer2.wait_for_window(r"^Mumble$")

      with subtest("Wait for certificate creation"):
        peer1.wait_for_window(r"^Mumble$")
        peer1.sleep(3) # mumble is slow to register handlers
        peer1.send_chars("\n")
        peer1.send_chars("\n")
        peer2.wait_for_window(r"^Mumble$")
        peer2.sleep(3) # mumble is slow to register handlers
        peer2.send_chars("\n")
        peer2.send_chars("\n")

      with subtest("Wait for server connect"):
        peer1.wait_for_window(r"^Mumble Server Connect$")
        peer2.wait_for_window(r"^Mumble Server Connect$")

      with subtest("Check validity of server certificates"):
        peer1.execute("killall .mumble-wrapped")
        peer1.sleep(1)
        peer1.execute("mumble mumble://peer2 >&2 &")
        peer1.wait_for_window(r"^Mumble$")
        peer1.sleep(3) # mumble is slow to register handlers
        peer1.send_chars("\n")
        peer1.send_chars("\n")
        peer1.wait_for_text("Connected.")

        peer2.execute("killall .mumble-wrapped")
        peer2.sleep(1)
        peer2.execute("mumble mumble://peer1 >&2 &")
        peer2.wait_for_window(r"^Mumble$")
        peer2.sleep(3) # mumble is slow to register handlers
        peer2.send_chars("\n")
        peer2.send_chars("\n")
        peer2.wait_for_text("Connected.")
    '';
  }
)
