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
      target=$2

      echo "installing secrets from $src to $target" >&2

      mkdir -p "$target".tmp "$target"
      if mountpoint -q "$target"; then
        mount -t tmpfs -o noswap -o private tmpfs "$target".tmp
        chmod 511 "$target".tmp
        mount --bind --make-private "$target".tmp "$target".tmp
        mount --bind --make-private "$target" "$target"
        tar -xf "$src" -C "$target".tmp
        move-mount --beneath --move "$target".tmp "$target" 2>/dev/null
        umount -R "$target".tmp
        rmdir "$target".tmp
        umount --lazy "$target"
      else
        mount -t tmpfs -o noswap tmpfs "$target"
        tar -xf "$src" -C "$target"
      fi
    '';
  };
  useSystemdActivation =
    (options.systemd ? sysusers && config.systemd.sysusers.enable)
    || (options.services ? userborn && config.services.userborn.enable);
  normalSecrets = lib.any (gen: lib.any (file: !file.neededForUsers) (lib.attrValues gen.files)) (
    lib.attrValues config.clan.core.vars.generators
  );
  userSecrets = lib.any (gen: lib.any (file: file.neededForUsers) (lib.attrValues gen.files)) (
    lib.attrValues config.clan.core.vars.generators
  );

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
              path =
                if file.config.neededFor == "users" then
                  "/run/user-secrets/${file.config.generatorName}/${file.config.name}"
                else if file.config.neededFor == "services" then
                  "/run/secrets/${file.config.generatorName}/${file.config.name}"
                else if file.config.neededFor == "activation" then
                  "${config.clan.password-store.secretLocation}/${file.config.generatorName}/${file.config.name}"
                else
                  throw "unknown neededFor ${file.config.neededFor}";

            };
          secretModule = "clan_cli.vars.secret_modules.password_store";
        };
    system.activationScripts =
      lib.mkIf ((config.clan.core.vars.settings.secretStore == "password-store") && !useSystemdActivation)
        {
          setupUserSecrets = lib.mkIf userSecrets (
            lib.stringAfter
              [
                "specialfs"
              ]
              ''
                [ -e /run/current-system ] || echo setting up secrets...
                ${installSecretTarball}/bin/install-secret-tarball ${config.clan.vars.password-store.secretLocation}/secrets_for_users.tar.gz /run/user-secrets
              ''
            // lib.optionalAttrs (config.system ? dryActivationScript) {
              supportsDryActivation = true;
            }
          );
          users.deps = lib.mkIf userSecrets [ "setupUserSecrets" ];
          setupSecrets = lib.mkIf normalSecrets (
            lib.stringAfter
              [
                "specialfs"
                "users"
                "groups"
              ]
              ''
                [ -e /run/current-system ] || echo setting up secrets...
                ${installSecretTarball}/bin/install-secret-tarball ${config.clan.vars.password-store.secretLocation}/secrets.tar.gz /run/secrets
              ''
            // lib.optionalAttrs (config.system ? dryActivationScript) {
              supportsDryActivation = true;
            }
          );
        };
    systemd.services =
      lib.mkIf ((config.clan.core.vars.settings.secretStore == "password-store") && useSystemdActivation)
        {
          pass-install-user-secrets = lib.mkIf userSecrets {
            wantedBy = [ "systemd-sysusers.service" ];
            before = [ "systemd-sysusers.service" ];
            unitConfig.DefaultDependencies = "no";

            serviceConfig = {
              Type = "oneshot";
              ExecStart = [
                "${installSecretTarball}/bin/install-secret-tarball ${config.clan.vars.password-store.secretLocation}/secrets_for_users.tar.gz /run/user-secrets"
              ];
              RemainAfterExit = true;
            };
          };
          pass-install-secrets = lib.mkIf normalSecrets {
            wantedBy = [ "sysinit.target" ];
            after = [ "systemd-sysusers.service" ];
            unitConfig.DefaultDependencies = "no";

            serviceConfig = {
              Type = "oneshot";
              ExecStart = [
                "${installSecretTarball}/bin/install-secret-tarball ${config.clan.vars.password-store.secretLocation}/secrets.tar.gz /run/secrets"
              ];
              RemainAfterExit = true;
            };
          };
        };
  };

}
