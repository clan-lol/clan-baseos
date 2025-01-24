{
  # Use this path to our repo root e.g. for UI test
  # inputs.clan-core.url = "../../../../.";

  # this placeholder is replaced by the path to clan-core
  inputs.clan-core.url = "__CLAN_CORE__";

  outputs =
    { self, clan-core }:
    let
      clan = clan-core.lib.buildClan {
        inherit self;
        meta.name = "test_flake_with_core_and_pass";
        machines = {
          vm1 =
            { lib, ... }:
            {
              imports = [
                clan-core.clanModules.sshd
                clan-core.clanModules.root-password
                clan-core.clanModules.user-password
              ];
              clan.user-password.user = "alice";
              clan.user-password.prompt = false;

              clan.core.networking.targetHost = "__CLAN_TARGET_ADDRESS__";
              system.stateVersion = lib.version;
              clan.core.facts.secretStore = "password-store";
              clan.core.facts.secretUploadDirectory = lib.mkForce "__CLAN_SOPS_KEY_DIR__/secrets";

              clan.core.networking.zerotier.controller.enable = true;

              systemd.services.shutdown-after-boot = {
                enable = true;
                wantedBy = [ "multi-user.target" ];
                after = [ "multi-user.target" ];
                script = ''
                  #!/usr/bin/env bash
                  shutdown -h now
                '';
              };
            };
        };
      };
    in
    {
      inherit (clan) nixosConfigurations clanInternals;
    };
}
