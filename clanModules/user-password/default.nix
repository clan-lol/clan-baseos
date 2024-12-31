{
  pkgs,
  config,
  lib,
  ...
}:
let
  cfg = config.clan.user-password;
in
{
  options.clan.user-password = {
    user = lib.mkOption {
      type = lib.types.str;
      example = "alice";
      description = "The user the password should be generated for.";
    };
    prompt = lib.mkOption {
      type = lib.types.bool;
      default = true;
      example = false;
      description = "Whether the user should be prompted.";
    };
  };

  config = {
    users.mutableUsers = false;
    users.users.${cfg.user} = {
      hashedPasswordFile = config.clan.core.facts.services.user-password.secret.user-password-hash.path;
      isNormalUser = lib.mkDefault true;
    };

    sops.secrets = lib.mkIf (config.clan.core.facts.secretStore == "sops") {
      "${config.clan.core.settings.machine.name}-user-password-hash".neededForUsers = true;
    };

    clan.core.facts.services.user-password = {
      secret.user-password = { };
      secret.user-password-hash = { };
      generator.prompt = (
        lib.mkIf config.clan.user-password.prompt "Set the password for your user '${config.clan.user-password.user}'.
      You can autogenerate a password, if you leave this prompt blank."
      );
      generator.path = with pkgs; [
        coreutils
        xkcdpass
        mkpasswd
      ];
      generator.script = ''
        if [[ -n ''${prompt_value-} ]]; then
          echo $prompt_value | tr -d "\n" > $secrets/user-password
        else
          xkcdpass --numwords 3 --delimiter - --count 1 | tr -d "\n" > $secrets/user-password
        fi
        cat $secrets/user-password | mkpasswd -s -m sha-512 | tr -d "\n" > $secrets/user-password-hash
      '';
    };
  };
}
