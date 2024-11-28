{
  config,
  lib,
  pkgs,
  ...
}:
let

  inherit (lib) flip;

  inherit (import ./funcs.nix { inherit lib; }) collectFiles;

  inherit (config.clan.core) machineName;

  secretPath =
    secret:
    if secret.share then
      config.clan.core.clanDir + "/vars/shared/${secret.generator}/${secret.name}/secret"
    else
      config.clan.core.clanDir
      + "/vars/per-machine/${machineName}/${secret.generator}/${secret.name}/secret";

  vars = collectFiles config.clan.core.vars;
in
{
  config.clan.core.vars.settings = lib.mkIf (config.clan.core.vars.settings.secretStore == "sops") {
    # Before we generate a secret we cannot know the path yet, so we need to set it to an empty string
    fileModule = file: {
      path = lib.mkIf file.config.secret (
        config.sops.secrets.${"vars/${file.config.generatorName}/${file.config.name}"}.path
          or "/no-such-path"
      );
    };
    secretModule = "clan_cli.vars.secret_modules.sops";
  };

  config.sops = lib.mkIf (config.clan.core.vars.settings.secretStore == "sops") {
    secrets = lib.listToAttrs (
      flip map vars (secret: {
        name = "vars/${secret.generator}/${secret.name}";
        value = {
          inherit (secret.sops) owner group;
          sopsFile = secretPath secret;
          format = "binary";
        };
      })
    );
    # To get proper error messages about missing secrets we need a dummy secret file that is always present
    defaultSopsFile = lib.mkIf config.sops.validateSopsFiles (
      lib.mkDefault (builtins.toString (pkgs.writeText "dummy.yaml" ""))
    );
    age.keyFile = lib.mkIf (builtins.pathExists (
      config.clan.core.clanDir + "/sops/secrets/${machineName}-age.key/secret"
    )) (lib.mkDefault "/var/lib/sops-nix/key.txt");
  };
}
