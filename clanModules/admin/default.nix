{ lib, config, ... }:
{
  options.clan.admin = {
    allowedKeys = lib.mkOption {
      default = [ ];
      type = lib.types.listOf lib.types.str;
      description = "The allowed public keys for ssh access to the admin user";
    };
  };
  imports = [
    ../sshd
    ../root-password
  ];
  config = {
    users.users.root.openssh.authorizedKeys.keys = config.clan.admin.allowedKeys;
  };
}
