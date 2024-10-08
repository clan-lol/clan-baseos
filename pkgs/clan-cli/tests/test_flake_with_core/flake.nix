{
  # Use this path to our repo root e.g. for UI test
  # inputs.clan-core.url = "../../../../.";

  # this placeholder is replaced by the path to nixpkgs
  inputs.clan-core.url = "__CLAN_CORE__";

  outputs =
    { self, clan-core }:
    let
      clan = clan-core.lib.buildClan {
        directory = self;
        meta.name = "test_flake_with_core";
        machines = {
          vm1 =
            { lib, ... }:
            {
              clan.core.networking.targetHost = "__CLAN_TARGET_ADDRESS__";
              system.stateVersion = lib.version;
              sops.age.keyFile = "__CLAN_SOPS_KEY_PATH__";
              clan.core.facts.secretUploadDirectory = "__CLAN_SOPS_KEY_DIR__";
              clan.core.sops.defaultGroups = [ "admins" ];
              clan.virtualisation.graphics = false;

              clan.core.networking.zerotier.controller.enable = true;
              networking.useDHCP = false;
            };
          vm2 =
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
              sops.age.keyFile = "__CLAN_SOPS_KEY_PATH__";
              clan.core.facts.secretUploadDirectory = "__CLAN_SOPS_KEY_DIR__";
              clan.core.networking.zerotier.networkId = "82b44b162ec6c013";
            };
        };
      };
    in
    {
      inherit (clan) nixosConfigurations clanInternals;
    };
}
