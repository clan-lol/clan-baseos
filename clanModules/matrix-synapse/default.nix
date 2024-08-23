{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.clan.matrix-synapse;
  element-web =
    pkgs.runCommand "element-web-with-config" { nativeBuildInputs = [ pkgs.buildPackages.jq ]; }
      ''
        cp -r ${pkgs.element-web} $out
        chmod -R u+w $out
        jq '."default_server_config"."m.homeserver" = { "base_url": "https://${cfg.app_domain}:443", "server_name": "${cfg.server_tld}" }' \
          > $out/config.json < ${pkgs.element-web}/config.json
        ln -s $out/config.json $out/config.${cfg.app_domain}.json
      '';
in
# FIXME: This was taken from upstream. Drop this when our patch is upstream
{
  options.services.matrix-synapse.package = lib.mkOption { readOnly = false; };
  options.clan.matrix-synapse = {
    server_tld = lib.mkOption {
      type = lib.types.str;
      description = "The address that is suffixed after your username i.e @alice:example.com";
      example = "example.com";
    };

    app_domain = lib.mkOption {
      type = lib.types.str;
      description = "The matrix server hostname also serves the element client";
      example = "matrix.example.com";
    };

    users = lib.mkOption {
      default = { };
      type = lib.types.attrsOf (
        lib.types.submodule (
          { name, ... }:
          {
            options = {
              name = lib.mkOption {
                type = lib.types.str;
                default = name;
                description = "The name of the user";
              };

              admin = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Whether the user should be an admin";
              };
            };
          }
        )
      );
      description = "A list of users. Not that only new users will be created and existing ones are not modified.";
      example.alice = {
        admin = true;
      };
    };
  };
  imports = [
    ../postgresql
    (lib.mkRemovedOptionModule [
      "clan"
      "matrix-synapse"
      "enable"
    ] "Importing the module will already enable the service.")
    ../nginx
  ];
  config = {
    services.matrix-synapse = {
      enable = true;
      settings = {
        server_name = cfg.server_tld;
        database = {
          args.user = "matrix-synapse";
          args.database = "matrix-synapse";
          name = "psycopg2";
        };
        turn_uris = [
          "turn:turn.matrix.org?transport=udp"
          "turn:turn.matrix.org?transport=tcp"
        ];
        registration_shared_secret_path = "/run/synapse-registration-shared-secret";
        listeners = [
          {
            port = 8008;
            bind_addresses = [ "::1" ];
            type = "http";
            tls = false;
            x_forwarded = true;
            resources = [
              {
                names = [ "client" ];
                compress = true;
              }
              {
                names = [ "federation" ];
                compress = false;
              }
            ];
          }
        ];
      };
    };

    systemd.tmpfiles.settings."01-matrix" = {
      "/run/synapse-registration-shared-secret" = {
        C.argument =
          config.clan.core.facts.services.matrix-synapse.secret.synapse-registration_shared_secret.path;
        z = {
          mode = "0400";
          user = "matrix-synapse";
        };
      };
    };

    clan.postgresql.users.matrix-synapse = { };
    clan.postgresql.databases.matrix-synapse.create.options = {
      TEMPLATE = "template0";
      LC_COLLATE = "C";
      LC_CTYPE = "C";
      ENCODING = "UTF8";
      OWNER = "matrix-synapse";
    };
    clan.postgresql.databases.matrix-synapse.restore.stopOnRestore = [ "matrix-synapse" ];

    clan.core.facts.services =
      {
        "matrix-synapse" = {
          secret."synapse-registration_shared_secret" = { };
          generator.path = with pkgs; [
            coreutils
            pwgen
          ];
          generator.script = ''
            echo -n "$(pwgen -s 32 1)" > "$secrets"/synapse-registration_shared_secret
          '';
        };
      }
      // lib.mapAttrs' (
        name: user:
        lib.nameValuePair "matrix-password-${user.name}" {
          secret."matrix-password-${user.name}" = { };
          generator.path = with pkgs; [ xkcdpass ];
          generator.script = ''
            xkcdpass -n 4 -d - > "$secrets"/${lib.escapeShellArg "matrix-password-${user.name}"}
          '';
        }
      ) cfg.users;

    systemd.services.matrix-synapse =
      let
        usersScript =
          ''
            while ! ${pkgs.netcat}/bin/nc -z -v ::1 8008; do
              if ! kill -0 "$MAINPID"; then exit 1; fi
              sleep 1;
            done
          ''
          + lib.concatMapStringsSep "\n" (user: ''
            # only create user if it doesn't exist
            /run/current-system/sw/bin/matrix-synapse-register_new_matrix_user --exists-ok --password-file ${
              config.clan.core.facts.services."matrix-password-${user.name}".secret."matrix-password-${user.name}".path
            } --user "${user.name}" ${if user.admin then "--admin" else "--no-admin"}
          '') (lib.attrValues cfg.users);
      in
      {
        path = [ pkgs.curl ];
        serviceConfig.ExecStartPost = [
          (''+${pkgs.writeShellScript "matrix-synapse-create-users" usersScript}'')
        ];
      };

    services.nginx = {
      enable = true;
      virtualHosts = {
        "${cfg.server_tld}" = {
          locations."= /.well-known/matrix/server".extraConfig = ''
            add_header Content-Type application/json;
            return 200 '${builtins.toJSON { "m.server" = "${cfg.app_domain}:443"; }}';
          '';
          locations."= /.well-known/matrix/client".extraConfig = ''
            add_header Content-Type application/json;
            add_header Access-Control-Allow-Origin *;
            return 200 '${
              builtins.toJSON {
                "m.homeserver" = {
                  "base_url" = "https://${cfg.app_domain}";
                };
                "m.identity_server" = {
                  "base_url" = "https://vector.im";
                };
              }
            }';
          '';
          forceSSL = true;
          enableACME = true;
        };
        "${cfg.app_domain}" = {
          forceSSL = true;
          enableACME = true;
          locations."/".root = element-web;
          locations."/_matrix".proxyPass = "http://localhost:8008";
          locations."/_synapse".proxyPass = "http://localhost:8008";
        };
      };
    };
  };
}
