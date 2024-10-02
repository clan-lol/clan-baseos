{ lib, config, ... }:
{
  options.clan.admin = {
    allowedKeys = lib.mkOption {
      default = { };
      type = lib.types.attrsOf lib.types.str;
      description = "The allowed public keys for ssh access to the admin user";
      example = {
        "key_1" = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQD...";
      };
    };
  };
  # Bad practice.
  # Should we add 'clanModules' to specialArgs?
  imports = [
    ../../sshd
    ../../root-password
  ];
  config = {
    users.users.root.openssh.authorizedKeys.keys = builtins.attrValues config.clan.admin.allowedKeys;
  };
}
