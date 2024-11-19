{
  config,
  pkgs,
  lib,
  ...
}:
let
  stringSet = list: builtins.attrNames (builtins.groupBy lib.id list);

  signArgs = builtins.concatStringsSep " " (
    builtins.map (domain: "-n ${lib.escapeShellArg "${config.clan.core.machineName}.${domain}"}") (
      stringSet config.clan.sshd.certificate.searchDomains
    )
  );
  cfg = config.clan.sshd;
in
{
  imports = [ ../shared.nix ];
  config = {
    services.openssh = {
      enable = true;
      settings.PasswordAuthentication = false;

      settings.HostCertificate = lib.mkIf (
        cfg.certificate.searchDomains != [ ]
      ) config.clan.core.vars.generators.openssh-cert.files."ssh.id_ed25519-cert.pub".path;

      hostKeys = [
        {
          path = config.clan.core.vars.generators.openssh.files."ssh.id_ed25519".path;
          type = "ed25519";
        }
      ];
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

    clan.core.vars.generators.openssh-cert = lib.mkIf (cfg.certificate.searchDomains != [ ]) {
      files."ssh.id_ed25519-cert.pub".secret = false;
      dependencies = [
        "openssh"
        "openssh-ca"
      ];
      runtimeInputs = [
        pkgs.openssh
        pkgs.jq
      ];
      script = ''
        ssh-keygen \
          -s $in/openssh-ca/id_ed25519 \
          -I ${config.clan.core.machineName} \
          ${builtins.toString signArgs} \
          $in/openssh/ssh.id_ed25519.pub
        mv $in/openssh/ssh.id_ed25519-cert.pub $out/ssh.id_ed25519-cert.pub
      '';
    };
  };
}
