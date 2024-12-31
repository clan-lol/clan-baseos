(import ../lib/container-test.nix) (
  { pkgs, ... }:
  {
    name = "deltachat";

    nodes.machine =
      { self, ... }:
      {
        imports = [
          self.clanModules.deltachat
          self.nixosModules.clanCore
          {
            clan.core.machineName = "machine";
            clan.core.settings.directory = ./.;
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
