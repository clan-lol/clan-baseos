{
  config,
  lib,
  pkgs,
  ...
}:
let

  inherit (lib) importJSON flip;

  inherit (builtins) dirOf pathExists;

  inherit (import ./funcs.nix { inherit lib; }) listVars;

  inherit (config.clan.core) machineName;

  metaFile = sopsFile: dirOf sopsFile + "/meta.json";

  metaData = sopsFile: if pathExists (metaFile sopsFile) then importJSON (metaFile sopsFile) else { };

  isSopsSecret =
    secret:
    let
      meta = metaData secret.sopsFile;
    in
    meta.store or null == "sops" && meta.deployed or true && meta.secret or true;

  varsDirMachines = config.clan.core.clanDir + "/vars/per-machine/${machineName}";
  varsDirShared = config.clan.core.clanDir + "/vars/shared";

  vars' = (listVars varsDirMachines) ++ (listVars varsDirShared);

  vars = lib.filter isSopsSecret vars';
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
    secretUploadDirectory = lib.mkDefault "/var/lib/sops-nix";
  };

  config.sops = lib.mkIf (config.clan.core.vars.settings.secretStore == "sops") {
    secrets = lib.listToAttrs (
      flip map vars (secret: {
        name = "vars/${secret.generator}/${secret.name}";
        value = {
          sopsFile = secret.sopsFile;
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
