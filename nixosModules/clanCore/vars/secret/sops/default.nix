{
  config,
  lib,
  pkgs,
  ...
}:
let

  inherit (import ./funcs.nix { inherit lib; }) collectFiles;

  machineName = config.clan.core.settings.machine.name;

  secretPath =
    secret:
    if secret.share then
      config.clan.core.settings.directory + "/vars/shared/${secret.generator}/${secret.name}/secret"
    else
      config.clan.core.settings.directory
      + "/vars/per-machine/${machineName}/${secret.generator}/${secret.name}/secret";

  vars = collectFiles config.clan.core.vars;
in
{
  config.clan.core.vars.settings = lib.mkIf (config.clan.core.vars.settings.secretStore == "sops") {
    # Before we generate a secret we cannot know the path yet, so we need to set it to an empty string
    fileModule = file: {
      path = lib.mkIf file.config.secret (
        if file.config.neededFor == "partitioning" then
          "/run/partitioning-secrets/${file.config.generatorName}/${file.config.name}"
        else if file.config.neededFor == "activation" then
          "/var/lib/sops-nix/activation/${file.config.generatorName}/${file.config.name}"
        else
          config.sops.secrets.${"vars/${file.config.generatorName}/${file.config.name}"}.path
            or "/no-such-path"
      );
    };
    secretModule = "clan_cli.vars.secret_modules.sops";
  };

  config.sops = lib.mkIf (config.clan.core.vars.settings.secretStore == "sops") {

    secrets = lib.listToAttrs (
      map (secret: {
        name = "vars/${secret.generator}/${secret.name}";
        value = {
          inherit (secret) owner group neededForUsers;
          sopsFile = secretPath secret;
          format = "binary";
        };
      }) (builtins.filter (x: builtins.pathExists (secretPath x)) vars)
    );

    # To get proper error messages about missing secrets we need a dummy secret file that is always present
    defaultSopsFile = lib.mkIf config.sops.validateSopsFiles (
      lib.mkDefault (builtins.toString (pkgs.writeText "dummy.yaml" ""))
    );
    age.keyFile = lib.mkIf (builtins.pathExists (
      config.clan.core.settings.directory + "/sops/secrets/${machineName}-age.key/secret"
    )) (lib.mkDefault "/var/lib/sops-nix/key.txt");
  };
}
