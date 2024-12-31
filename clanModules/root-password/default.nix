{
  pkgs,
  config,
  lib,
  ...
}:
{
  users.mutableUsers = false;
  users.users.root.hashedPasswordFile =
    config.clan.core.facts.services.root-password.secret.password-hash.path;

  sops.secrets = lib.mkIf (config.clan.core.facts.secretStore == "sops") {
    "${config.clan.core.settings.machine.name}-password-hash".neededForUsers = true;
  };

  clan.core.facts.services.root-password = {
    secret.password = { };
    secret.password-hash = { };
    generator.path = with pkgs; [
      coreutils
      xkcdpass
      mkpasswd
    ];
    generator.script = ''
      xkcdpass --numwords 3 --delimiter - --count 1 | tr -d "\n" > $secrets/password
      cat $secrets/password | mkpasswd -s -m sha-512 | tr -d "\n" > $secrets/password-hash
    '';
  };
}
