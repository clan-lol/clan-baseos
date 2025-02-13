{
  config,
  lib,
  ...
}:
{
  config.clan.core.vars.settings = lib.mkIf (config.clan.core.vars.settings.secretStore == "fs") {
    fileModule = file: {
      path =
        if file.config.neededFor == "partitioning" then
          throw "${file.config.generatorName}/${file.config.name}: FS backend does not support partitioning."
        else
          "/run/secrets/${file.config.generatorName}/${file.config.name}";
    };
    secretModule = "clan_cli.vars.secret_modules.fs";
  };
}
