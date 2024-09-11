{ config, lib, ... }:
{
  config.clan.core.vars.settings =
    lib.mkIf (config.clan.core.vars.settings.publicStore == "in_repo")
      {
        publicModule = "clan_cli.vars.public_modules.in_repo";
        fileModule = file: {
          path = lib.mkIf (file.config.secret == false) (
            if file.config.share then
              (config.clan.core.clanDir + "/vars/shared/${file.config.generatorName}/${file.config.name}/value")
            else
              (
                config.clan.core.clanDir
                + "/vars/per-machine/${config.clan.core.machineName}/${file.config.generatorName}/${file.config.name}/value"
              )
          );
          value = lib.mkIf (file.config.secret == false) (lib.readFile file.config.path);
        };
      };
}
