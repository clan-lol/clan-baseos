{ config, lib, ... }:
let
  inherit (lib)
    mkOptionDefault
    mkIf
    readFile
    pathExists
    ;
in
{
  config.clan.core.vars.settings = mkIf (config.clan.core.vars.settings.publicStore == "in_repo") {
    publicModule = "clan_cli.vars.public_modules.in_repo";
    fileModule = file: {
      path = mkIf (file.config.secret == false) (
        if file.config.share then
          (
            config.clan.core.settings.directory
            + "/vars/shared/${file.config.generatorName}/${file.config.name}/value"
          )
        else
          (
            config.clan.core.settings.directory
            + "/vars/per-machine/${config.clan.core.settings.machine.name}/${file.config.generatorName}/${file.config.name}/value"
          )
      );
      value = mkIf (file.config.secret == false) (
        # dynamically adjust priority to allow overriding with mkDefault in case the file is not found
        if (pathExists file.config.path) then
          # if the file is found it should have normal priority
          readFile file.config.path
        else
          # if the file is not found, we want to downgrade the priority, to allow overriding via mkDefault
          mkOptionDefault (readFile file.config.path)
      );
    };
  };
}
