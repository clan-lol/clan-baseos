{
  config,
  options,
  lib,
  pkgs,
  ...
}:
let
  installSecretTarball = pkgs.writeShellApplication {
    name = "install-secret-tarball";
    runtimeInputs = [
      pkgs.gnutar
      pkgs.gzip
      pkgs.move-mount-beneath
    ];
    text = ''
      set -efu -o pipefail

      src=$1
      mkdir -p /run/secrets.tmp /run/secrets
      if mountpoint -q /run/secrets; then
        mount -t tmpfs -o noswap -o private tmpfs /run/secrets.tmp
        chmod 511 /run/secrets.tmp
        mount --bind --make-private /run/secrets.tmp /run/secrets.tmp
        mount --bind --make-private /run/secrets /run/secrets
        tar -xf "$src" -C /run/secrets.tmp
        move-mount --beneath --move /run/secrets.tmp /run/secrets >/dev/null
        umount -R /run/secrets.tmp
        rmdir /run/secrets.tmp
        umount --lazy /run/secrets
      else
        mount -t tmpfs -o noswap tmpfs /run/secrets
        tar -xf "$src" -C /run/secrets
      fi
    '';
  };
  useSystemdActivation =
    (options.systemd ? sysusers && config.systemd.sysusers.enable)
    || (options.services ? userborn && config.services.userborn.enable);
in
{
  options.clan.vars.password-store = {
    secretLocation = lib.mkOption {
      type = lib.types.path;
      default = "/etc/secret-vars";
      description = ''
        location where the tarball with the password-store secrets will be uploaded to and the manifest
      '';
    };
  };
  config = {
    system.clan.deployment.data.password-store.secretLocation =
      config.clan.vars.password-store.secretLocation;
    clan.core.vars.settings =
      lib.mkIf (config.clan.core.vars.settings.secretStore == "password-store")
        {
          fileModule =
            file:
            lib.mkIf file.config.secret {
              path = "/run/secrets/${file.config.generatorName}/${file.config.name}";
            };
          secretModule = "clan_cli.vars.secret_modules.password_store";
        };
    system.activationScripts.setupSecrets =
      lib.mkIf
        (
          (config.clan.core.vars.settings.secretStore == "password-store")
          && (config.clan.core.vars.generators != { } && !useSystemdActivation)
        )
        (
          lib.stringAfter
            [
              "specialfs"
              "users"
              "groups"
            ]
            ''
              [ -e /run/current-system ] || echo setting up secrets...
              ${installSecretTarball}/bin/install-secret-tarball ${config.clan.password-store.secretLocation}/secrets.tar.gz
            ''
          // lib.optionalAttrs (config.system ? dryActivationScript) {
            supportsDryActivation = true;
          }
        );
    systemd.services.pass-install-secrets =
      lib.mkIf
        (
          (config.clan.core.vars.settings.secretStore == "password-store")
          && (config.clan.core.vars.generators != { } && useSystemdActivation)
        )
        {
          wantedBy = [ "sysinit.target" ];
          after = [ "systemd-sysusers.service" ];
          unitConfig.DefaultDependencies = "no";

          serviceConfig = {
            Type = "oneshot";
            ExecStart = [
              "${installSecretTarball}/bin/install-secret-tarball ${config.clan.password-store.secretLocation}/secrets.tar.gz"
            ];
            RemainAfterExit = true;
          };
        };
  };

}
