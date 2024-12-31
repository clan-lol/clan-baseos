(import ../lib/test-base.nix) {
  name = "secrets";

  nodes.machine =
    { self, config, ... }:
    {
      environment.etc."privkey.age".source = ./key.age;
      imports = [ (self.nixosModules.clanCore) ];
      environment.etc."secret".source = config.sops.secrets.secret.path;
      environment.etc."group-secret".source = config.sops.secrets.group-secret.path;
      sops.age.keyFile = "/etc/privkey.age";

      clan.core.settings.directory = "${./.}";
      clan.core.settings.machine.name = "machine";

      networking.hostName = "machine";
    };
  testScript = ''
    machine.succeed("cat /etc/secret >&2")
    machine.succeed("cat /etc/group-secret >&2")
  '';
}
