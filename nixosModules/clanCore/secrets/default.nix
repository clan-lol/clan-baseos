{ config, lib, pkgs, ... }:
{
  options.clanCore.secretStore = lib.mkOption {
    type = lib.types.enum [ "sops" "password-store" "custom" ];
    default = "sops";
    description = ''
      method to store secrets
      custom can be used to define a custom secret store.
      one would have to define system.clan.generateSecrets and system.clan.uploadSecrets
    '';
  };
  options.clanCore.secrets = lib.mkOption {
    default = { };
    type = lib.types.attrsOf
      (lib.types.submodule (secret: {
        options = {
          name = lib.mkOption {
            type = lib.types.str;
            default = secret.config._module.args.name;
            description = ''
              namespace of the secret
            '';
          };
          generator = lib.mkOption {
            type = lib.types.nullOr lib.types.str;
            description = ''
              script to generate the secret.
              can be set to null. then the user has to provide the secret via the clan cli
            '';
          };
          secrets = lib.mkOption {
            type = lib.types.attrsOf (lib.types.submodule (secret: {
              options = {
                name = lib.mkOption {
                  type = lib.types.str;
                  description = ''
                    name of the secret
                  '';
                  default = secret.config._module.args.name;
                };
              };
            }));
            description = ''
              path where the secret is located in the filesystem
            '';
          };
          facts = lib.mkOption {
            type = lib.types.attrsOf (lib.types.submodule (fact: {
              options = {
                name = lib.mkOption {
                  type = lib.types.str;
                  description = ''
                    name of the fact
                  '';
                  default = fact.config._module.args.name;
                };
                path = lib.mkOption {
                  type = lib.types.str;
                  description = ''
                    path to a fact which is generated by the generator
                  '';
                  default = "machines/${config.clanCore.machineName}/facts/${fact.config._module.args.name}";
                };
                value = lib.mkOption {
                  defaultText = lib.literalExpression "\${config.clanCore.clanDir}/\${fact.config.path}";
                  default = builtins.readFile "${config.clanCore.clanDir}/${fact.config.path}";
                };
              };
            }));
          };
        };
      }));
  };
  config.system.build.generateUploadSecrets = pkgs.writeScript "generate_upload_secrets" ''
    ${config.system.clan.generateSecrets}
    ${config.system.clan.uploadSecrets}
  '';
  imports = [
    ./sops.nix
    ./password-store.nix
  ];
}
