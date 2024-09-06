(import ../lib/container-test.nix) (
  { pkgs, ... }:
  {
    name = "secrets";

    nodes.machine =
      { self, ... }:
      {
        imports = [
          self.clanModules.deltachat
          self.nixosModules.clanCore
          {
            clan.core.machineName = "machine";
            clan.core.clanDir = ./.;
            clan.core.machine = {
              id = "a73f5245cdba4576ab6cfef3145ac9ec";
              diskId = "c4c47b";
            };
          }
        ];
      };
    testScript = ''
      start_all()
      machine.wait_for_unit("maddy")
      # imap
      machine.succeed("${pkgs.netcat}/bin/nc -z -v ::1 143")
      # smtp submission
      machine.succeed("${pkgs.netcat}/bin/nc -z -v ::1 587")
      # smtp
      machine.succeed("${pkgs.netcat}/bin/nc -z -v ::1 25")
    '';
  }
)
