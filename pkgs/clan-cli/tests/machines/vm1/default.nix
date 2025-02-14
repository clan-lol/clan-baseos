{ config, ... }:
{
  clan.core.networking.targetHost = "__CLAN_TARGET_ADDRESS__";
  system.stateVersion = config.system.nixos.release;
  sops.age.keyFile = "__CLAN_SOPS_KEY_PATH__";
  clan.core.facts.secretUploadDirectory = "__CLAN_SOPS_KEY_DIR__";
  clan.virtualisation.graphics = false;

  clan.core.facts.networking.zerotier.controller.enable = true;
  networking.useDHCP = false;

  systemd.services.shutdown-after-boot = {
    enable = true;
    wantedBy = [ "multi-user.target" ];
    after = [ "multi-user.target" ];
    script = ''
      #!/usr/bin/env bash
      shutdown -h now
    '';
  };
}
