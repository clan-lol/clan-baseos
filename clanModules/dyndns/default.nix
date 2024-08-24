{
  config,
  pkgs,
  lib,
  ...
}:

let
  name = "dyndns";
  cfg = config.clan.${name};

  # We dedup secrets if they have the same provider + base domain
  secret_id = opt: "${name}-${opt.provider}-${opt.domain}";
  secret_path =
    opt: config.clan.core.facts.services."${secret_id opt}".secret."${secret_id opt}".path;

  # We check that a secret has not been set in extraSettings.
  extraSettingsSafe =
    opt:
    if (builtins.hasAttr opt.secret_field_name opt.extraSettings) then
      throw "Please do not set ${opt.secret_field_name} in extraSettings, it is automatically set by the dyndns module."
    else
      opt.extraSettings;
  /*
    We go from:
    {home.example.com:{value:{domain:example.com,host:home, provider:namecheap}}}
    To:
    {settings: [{domain: example.com, host: home, provider: namecheap, password: dyndns-namecheap-example.com}]}
  */
  service_config = {
    settings = builtins.catAttrs "value" (
      builtins.attrValues (
        lib.mapAttrs (_: opt: {
          value =
            (extraSettingsSafe opt)
            // {
              domain = opt.domain;
              provider = opt.provider;
            }
            // {
              "${opt.secret_field_name}" = secret_id opt;
            };
        }) cfg.settings
      )
    );
  };

  secret_generator = _: opt: {
    name = secret_id opt;
    value = {
      secret.${secret_id opt} = { };
      generator.prompt = "Dyndns passphrase for ${secret_id opt}";
      generator.script = ''
        echo "$prompt_value" > $secrets/${secret_id opt}
      '';
    };
  };
in
{
  options.clan.${name} = {
    server = {
      enable = lib.mkEnableOption "dyndns webserver";
      domain = lib.mkOption {
        type = lib.types.str;
        description = "Domain to serve the webservice on";
      };
      port = lib.mkOption {
        type = lib.types.int;
        default = 54805;
        description = "Port to listen on";
      };
    };

    period = lib.mkOption {
      type = lib.types.int;
      default = 5;
      description = "Domain update period in minutes";
    };

    settings = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule (
          { ... }:
          {
            options = {
              provider = lib.mkOption {
                example = "namecheap";
                type = lib.types.str;
                description = "The dyndns provider to use";
              };
              domain = lib.mkOption {
                type = lib.types.str;
                example = "example.com";
                description = "The top level domain to update.";
              };
              secret_field_name = lib.mkOption {
                example = [
                  "password"
                  "api_key"
                ];
                type = lib.types.enum [
                  "password"
                  "token"
                  "api_key"
                ];
                default = "password";
                description = "The field name for the secret";
              };
              # TODO: Ideally we would create a gigantic list of all possible settings / types
              # optimally we would have a way to generate the options from the source code
              extraSettings = lib.mkOption {
                type = lib.types.attrsOf lib.types.str;
                default = { };
                description = ''
                  Extra settings for the provider.
                  Provider specific settings: https://github.com/qdm12/ddns-updater#configuration
                '';
              };
            };
          }
        )
      );
      default = [ ];
      description = "Configuration for which domains to update";
    };
  };

  imports = [
    (lib.mkRemovedOptionModule [
      "clan"
      "dyndns"
      "enable"
    ] "Just define clan.dyndns.settings to enable it")
    ../nginx
  ];

  config = lib.mkMerge [
    (lib.mkIf (cfg.settings != { }) {
      clan.core.facts.services = lib.mapAttrs' secret_generator cfg.settings;

      users.groups.${name} = { };
      users.users.${name} = {
        group = name;
        isSystemUser = true;
        description = "User for ${name} service";
        home = "/var/lib/${name}";
        createHome = true;
      };

      services.nginx = lib.mkIf cfg.server.enable {
        enable = true;
        virtualHosts = {
          "${cfg.server.domain}" = {
            forceSSL = true;
            enableACME = true;
            locations."/" = {
              proxyPass = "http://localhost:${toString cfg.server.port}";
            };
          };
        };
      };

      systemd.services.${name} = {
        path = [ ];
        description = "Dynamic DNS updater";
        after = [ "network.target" ];
        wantedBy = [ "multi-user.target" ];
        environment = {
          MYCONFIG = "${builtins.toJSON service_config}";
          SERVER_ENABLED = if cfg.server.enable then "yes" else "no";
          PERIOD = "${toString cfg.period}m";
          LISTENING_ADDRESS = ":${toString cfg.server.port}";
        };

        serviceConfig =
          let
            pyscript = pkgs.writers.writePyPy3Bin "test.py" { libraries = [ ]; } ''
              import json
              from pathlib import Path
              import os

              cred_dir = Path(os.getenv("CREDENTIALS_DIRECTORY"))
              config_str = os.getenv("MYCONFIG")


              def get_credential(name):
                  secret_p = cred_dir / name
                  with open(secret_p, 'r') as f:
                      return f.read().strip()


              config = json.loads(config_str)
              print(f"Config: {config}")
              for attrset in config["settings"]:
                  if "password" in attrset:
                      attrset['password'] = get_credential(attrset['password'])
                  elif "token" in attrset:
                      attrset['token'] = get_credential(attrset['token'])
                  elif "api_key" in attrset:
                      attrset['api_key'] = get_credential(attrset['api_key'])
                  else:
                      raise ValueError(f"Missing secret field in {attrset}")

              # create directory data if it does not exist
              data_dir = Path('data')
              data_dir.mkdir(mode=0o770, exist_ok=True)

              # Write the config with secrets back
              config_path = data_dir / 'config.json'
              with open(config_path, 'w') as f:
                  f.write(json.dumps(config, indent=4))

              # Set file permissions to read and write
              # only by the user and group
              config_path.chmod(0o660)

              # Set file permissions to read
              # and write only by the user and group
              for file in data_dir.iterdir():
                  file.chmod(0o660)
            '';
          in
          {
            ExecStartPre = lib.getExe pyscript;
            ExecStart = lib.getExe pkgs.ddns-updater;
            LoadCredential = lib.mapAttrsToList (_: opt: "${secret_id opt}:${secret_path opt}") cfg.settings;
            User = name;
            Group = name;
            NoNewPrivileges = true;
            PrivateTmp = true;
            ProtectSystem = "strict";
            ReadOnlyPaths = "/";
            PrivateDevices = "yes";
            ProtectKernelModules = "yes";
            ProtectKernelTunables = "yes";
            WorkingDirectory = "/var/lib/${name}";
            ReadWritePaths = [
              "/proc/self"
              "/var/lib/${name}"
            ];

            Restart = "always";
            RestartSec = 60;
          };
      };
    })
  ];
}
