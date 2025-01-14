{
  pkgs,
  config,
  ...
}:
{
  users.mutableUsers = false;
  users.users.root.hashedPasswordFile =
    config.clan.core.vars.generators.root-password.files.password-hash.path;

  clan.core.vars.generators.root-password = {
    files.password-hash = {
      neededFor = "users";
    };
    migrateFact = "root-password";
    runtimeInputs = [
      pkgs.coreutils
      pkgs.mkpasswd
      pkgs.xkcdpass
    ];
    prompts.password.createFile = true;
    prompts.password.type = "hidden";
    prompts.password.description = "You can autogenerate a password, if you leave this prompt blank.";

    script = ''
      prompt_value=$(cat $prompts/password)
      if [[ -n ''${prompt_value-} ]]; then
        echo $prompt_value | tr -d "\n" > $out/password
      else
        xkcdpass --numwords 3 --delimiter - --count 1 | tr -d "\n" > $out/password
      fi
      mkpasswd -s -m sha-512 <  $out/password | tr -d "\n" > $out/password-hash
    '';
  };
}
