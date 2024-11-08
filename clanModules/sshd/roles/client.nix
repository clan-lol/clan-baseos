{ ... }:
{
  imports = [
    ../shared.nix
  ];
  programs.ssh.knownHosts.ssh-ca = lib.mkIf (config.clan.sshd.certificate.searchDomains != [ ]) {
    certAuthority = true;
    extraHostNames = builtins.map (domain: "*.${domain}") config.clan.sshd.certificate.searchDomains;
    publicKey = config.clan.core.vars.generators.openssh-ca.files."id_ed25519.pub".value;
  };
}
