(import ../lib/container-test.nix) (
  { pkgs, ... }:
  {
    name = "zt-tcp-relay";

    nodes.machine =
      { self, ... }:
      {
        imports = [
          self.nixosModules.clanCore
          self.clanModules.zt-tcp-relay
          {
            clan.core.machineName = "machine";
            clan.core.clanDir = ./.;
            clan.core.machine = {
              id = "df97124f09da48e3a22d77ce30ee8da6";
              diskId = "c9c52c";
            };
          }
        ];
      };
    testScript = ''
      start_all()
      machine.wait_for_unit("zt-tcp-relay.service")
      out = machine.succeed("${pkgs.netcat}/bin/nc -z -v localhost 4443")
      print(out)
    '';
  }
)
