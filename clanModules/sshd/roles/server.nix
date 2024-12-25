{
  config,
  pkgs,
  lib,
  ...
}:
let
  stringSet = list: builtins.attrNames (builtins.groupBy lib.id list);

  domains = stringSet config.clan.sshd.certificate.searchDomains;

  cfg = config.clan.sshd;
in
{
  imports = [ ../shared.nix ];
  options = {
    clan.sshd.hostKeys.rsa.enable = lib.mkEnableOption "Generate RSA host key";
  };
  config = {
    services.openssh = {
      enable = true;
      settings.PasswordAuthentication = false;

      settings.HostCertificate = lib.mkIf (
        cfg.certificate.searchDomains != [ ]
      ) config.clan.core.vars.generators.openssh-cert.files."ssh.id_ed25519-cert.pub".path;

      hostKeys =
        [
          {
            path = config.clan.core.vars.generators.openssh.files."ssh.id_ed25519".path;
            type = "ed25519";
          }
        ]
        ++ lib.optional cfg.hostKeys.rsa.enable {
          path = config.clan.core.vars.generators.openssh-rsa.files."ssh.id_rsa".path;
          type = "rsa";
        };
    };
    clan.core.vars.generators.openssh = {
      files."ssh.id_ed25519" = { };
      files."ssh.id_ed25519.pub".secret = false;
      migrateFact = "openssh";
      runtimeInputs = [
        pkgs.coreutils
        pkgs.openssh
      ];
      script = ''
        ssh-keygen -t ed25519 -N "" -f $out/ssh.id_ed25519
      '';
    };

    clan.core.vars.generators.openssh-rsa = lib.mkIf config.clan.sshd.hostKeys.rsa.enable {
      files."ssh.id_rsa" = { };
      files."ssh.id_rsa.pub".secret = false;
      migrateFact = "openssh";
      runtimeInputs = [
        pkgs.coreutils
        pkgs.openssh
      ];
      script = ''
        ssh-keygen -t rsa -b 4096 -N "" -f $out/ssh.id_rsa
      '';
    };

    clan.core.vars.generators.openssh-cert = lib.mkIf (cfg.certificate.searchDomains != [ ]) {
      files."ssh.id_ed25519-cert.pub".secret = false;
      dependencies = [
        "openssh"
        "openssh-ca"
      ];
      validation = {
        name = config.clan.core.machineName;
        domains = lib.genAttrs config.clan.sshd.certificate.searchDomains lib.id;
      };
      runtimeInputs = [
        pkgs.openssh
        pkgs.jq
      ];
      script = ''
        ssh-keygen \
          -s $in/openssh-ca/id_ed25519 \
          -I ${config.clan.core.machineName} \
          -h \
          -n ${lib.concatMapStringsSep "," (d: "${config.clan.core.machineName}.${d}") domains} \
          $in/openssh/ssh.id_ed25519.pub
        mv $in/openssh/ssh.id_ed25519-cert.pub $out/ssh.id_ed25519-cert.pub
      '';
    };
  };
}
