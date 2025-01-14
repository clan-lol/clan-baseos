{
  config,
  lib,
  ...
}:
{
  config.clan.core.vars.settings = lib.mkIf (config.clan.core.vars.settings.secretStore == "vm") {
    fileModule = file: {
      path = "/etc/secrets/${file.config.generatorName}/${file.config.name}";
    };
    secretModule = "clan_cli.vars.secret_modules.vm";
  };
}
