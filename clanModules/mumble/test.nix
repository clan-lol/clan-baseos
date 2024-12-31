{ pkgs, self, ... }:
pkgs.nixosTest {
  name = "mumble";
  nodes.peer1 =
    { ... }:
    {
      imports = [
        self.nixosModules.mumble
        self.inputs.clan-core.nixosModules.clanCore
        {
          config = {
            clan.core.machineName = "peer1";
            clan.core.settings.directory = ./.;

            documentation.enable = false;
          };
        }
      ];
    };
  nodes.peer2 =
    { ... }:
    {
      imports = [
        self.nixosModules.mumble
        self.inputs.clan-core.nixosModules.clanCore
        {
          config = {

            clan.core.machineName = "peer2";
            clan.core.settings.directory = ./.;

            documentation.enable = false;
          };
        }
      ];
    };

  testScript = ''
    start_all()
  '';

}
