{ config, lib, ... }:
{
  config.clan.core.vars.settings =
    lib.mkIf (config.clan.core.vars.settings.secretStore == "password-store")
      {
        fileModule = file: {
          path = lib.mkIf file.config.secret "${config.clan.core.vars.settings.secretUploadDirectory}/vars/${file.config.generatorName}/${file.config.name}";
        };
        secretUploadDirectory = lib.mkDefault "/etc/secrets";
        secretModule = "clan_cli.vars.secret_modules.password_store";
      };
}
