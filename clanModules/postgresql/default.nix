{
  pkgs,
  lib,
  config,
  ...
}:
let
  createDatabaseState =
    db:
    let
      folder = "/var/backup/postgres/${db.name}";
      current = "${folder}/pg-dump";
      compression = lib.optionalString (lib.versionAtLeast config.services.postgresql.package.version "16") "--compress=zstd";
    in
    {
      folders = [ folder ];
      preBackupScript = ''
        export PATH=${
          lib.makeBinPath [
            config.services.postgresql.package
            config.systemd.package
            pkgs.coreutils
            pkgs.util-linux
            pkgs.zstd
          ]
        }
        while [[ "$(systemctl is-active postgresql)" == activating ]]; do
          sleep 1
        done

        mkdir -p "${folder}"
        runuser -u postgres -- pg_dump ${compression} --dbname=${db.name} -Fc -c > "${current}.tmp"
        mv "${current}.tmp" ${current}
      '';
      postRestoreScript = ''
        export PATH=${
          lib.makeBinPath [
            config.services.postgresql.package
            config.systemd.package
            pkgs.coreutils
            pkgs.util-linux
            pkgs.zstd
            pkgs.gnugrep
          ]
        }
        while [[ "$(systemctl is-active postgresql)" == activating ]]; do
          sleep 1
        done
        echo "Waiting for postgres to be ready..."
        while ! runuser -u postgres -- psql --port=${builtins.toString config.services.postgresql.settings.port} -d postgres -c "" ; do
          if ! systemctl is-active postgresql; then exit 1; fi
          sleep 0.1
        done

        if [[ -e "${current}" ]]; then
          (
            systemctl stop ${lib.concatStringsSep " " db.restore.stopOnRestore}
            trap "systemctl start ${lib.concatStringsSep " " db.restore.stopOnRestore}" EXIT

            mkdir -p "${folder}"
            if runuser -u postgres -- psql -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '${db.name}'" | grep -q 1; then
              runuser -u postgres -- dropdb "${db.name}"
            fi
            runuser -u postgres -- pg_restore -C -d postgres "${current}"
          )
        else
          echo No database backup found, skipping restore
        fi
      '';
    };

  createDatabase = db: ''
    CREATE DATABASE "${db.name}" ${
      lib.concatStringsSep " " (
        lib.mapAttrsToList (name: value: "${name} = '${value}'") db.create.options
      )
    }
  '';
  cfg = config.clan.postgresql;

  userClauses = lib.mapAttrsToList (
    _: user:
    ''$PSQL -tAc "SELECT 1 FROM pg_roles WHERE rolname='${user.name}'" | grep -q 1 || $PSQL -tAc 'CREATE USER "${user.name}"' ''
  ) cfg.users;
  databaseClauses = lib.mapAttrsToList (
    name: db:
    lib.optionalString db.create.enable ''$PSQL -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '${name}'" | grep -q 1 || $PSQL -d postgres -c ${lib.escapeShellArg (createDatabase db)} ''
  ) cfg.databases;
in
{
  options.clan.postgresql = {
    # we are reimplemeting ensureDatabase and ensureUser options here to allow to create databases with options
    databases = lib.mkOption {
      description = "Databases to create";
      default = { };
      type = lib.types.attrsOf (
        lib.types.submodule (
          { name, ... }:
          {
            options = {
              name = lib.mkOption {
                type = lib.types.str;
                default = name;
                description = "Database name.";
              };
              service = lib.mkOption {
                type = lib.types.str;
                default = name;
                description = "Service name that we associate with the database.";
              };
              # set to false, in case the upstream module uses ensureDatabase option
              create.enable = lib.mkOption {
                type = lib.types.bool;
                default = true;
                description = "Create the database if it does not exist.";
              };
              create.options = lib.mkOption {
                description = "Options to pass to the CREATE DATABASE command.";
                type = lib.types.lazyAttrsOf lib.types.str;
                default = { };
                example = {
                  TEMPLATE = "template0";
                  LC_COLLATE = "C";
                  LC_CTYPE = "C";
                  ENCODING = "UTF8";
                  OWNER = "foo";
                };
              };
              restore.stopOnRestore = lib.mkOption {
                type = lib.types.listOf lib.types.str;
                default = [ ];
                description = "List of systemd services to stop before restoring the database.";
              };
            };
          }
        )
      );
    };
    users = lib.mkOption {
      description = "Users to create";
      default = { };
      type = lib.types.attrsOf (
        lib.types.submodule (
          { name, ... }:
          {
            options.name = lib.mkOption {
              description = "User name";
              type = lib.types.str;
              default = name;
            };
          }
        )
      );
    };
  };
  config = {
    services.postgresql.settings = {
      wal_level = "replica";
      max_wal_senders = 3;
    };

    services.postgresql.enable = true;
    # We are duplicating a bit the upstream module but allow to create databases with options
    systemd.services.postgresql.postStart = ''
      PSQL="psql --port=${builtins.toString config.services.postgresql.settings.port}"

      while ! $PSQL -d postgres -c "" 2> /dev/null; do
        if ! kill -0 "$MAINPID"; then exit 1; fi
        sleep 0.1
      done
      ${lib.concatStringsSep "\n" userClauses}
      ${lib.concatStringsSep "\n" databaseClauses}
    '';

    clan.core.state = lib.mapAttrs' (
      _: db: lib.nameValuePair db.service (createDatabaseState db)
    ) config.clan.postgresql.databases;

    environment.systemPackages = builtins.map (
      db:
      let
        folder = "/var/backup/postgres/${db.name}";
        current = "${folder}/pg-dump";
      in
      pkgs.writeShellScriptBin "postgres-db-restore-command-${db.name}" ''
        export PATH=${
          lib.makeBinPath [
            config.services.postgresql.package
            config.systemd.package
            pkgs.coreutils
            pkgs.util-linux
            pkgs.zstd
            pkgs.gnugrep
          ]
        }
        while [[ "$(systemctl is-active postgresql)" == activating ]]; do
          sleep 1
        done
        echo "Waiting for postgres to be ready..."
        while ! runuser -u postgres -- psql --port=${builtins.toString config.services.postgresql.settings.port} -d postgres -c "" ; do
          if ! systemctl is-active postgresql; then exit 1; fi
          sleep 0.1
        done

        if [[ -e "${current}" ]]; then
          (
            ${lib.optionalString (db.restore.stopOnRestore != [ ]) ''
              systemctl stop ${builtins.toString db.restore.stopOnRestore}
              trap "systemctl start ${builtins.toString db.restore.stopOnRestore}" EXIT
            ''}

            mkdir -p "${folder}"
            if runuser -u postgres -- psql -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '${db.name}'" | grep -q 1; then
              runuser -u postgres -- dropdb "${db.name}"
            fi
            runuser -u postgres -- pg_restore -C -d postgres "${current}"
          )
        else
          echo No database backup found, skipping restore
        fi
      ''
    ) (builtins.attrValues config.clan.postgresql.databases);
  };
}
