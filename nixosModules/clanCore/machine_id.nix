{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.clan.core.machine;
in
{
  options.clan.core.machine = {
    id = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      description = "The machine id";
    };
    idShort = lib.mkOption {
      readOnly = true;
      type = lib.types.nullOr lib.types.str;
      description = "The short machine id";
    };
    diskId = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      description = "The disk id";
    };
  };

  config = {
    clan.core.machine.id =
      lib.mkDefault
        config.clan.core.facts.services."machine_id".public."machine_id".value;
    clan.core.machine.idShort = if (cfg.id != null) then (lib.substring 0 8 cfg.id) else null;

    clan.core.machine.diskId =
      lib.mkDefault
        config.clan.core.facts.services."machine_id".public."diskId".value;

    clan.core.facts.services."machine_id" = {
      public."machine_id" = { };
      public."diskId" = { };
      generator.path = [
        pkgs.coreutils
      ];
      generator.script = ''
        machine_uuid=$(dd if=/dev/urandom bs=1 count=16 2>/dev/null | od -An -tx1 | tr -d ' \n')
        disk_uuid=$(dd if=/dev/urandom bs=1 count=3 2>/dev/null | od -An -tx1 | tr -d ' \n')
        echo -n "$machine_uuid" > "$facts"/machine_id
        echo -n "$disk_uuid" > "$facts"/diskId
      '';
    };

    networking.hostId = lib.mkIf (cfg.id != null) (lib.mkDefault cfg.idShort);

    boot.kernelParams = lib.mkIf (cfg.id != null) [
      ''systemd.machine_id=${cfg.id}''
    ];
  };
}
