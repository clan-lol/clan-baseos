{
  config,
  lib,
  ...
}:
let

  cfg = config.clan.factless;
in
{
  # These options are reexported here to allow the inventory to set them
  options.clan.factless = {
    machineId = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      description = "A machine id based on the UUID v4 format";
      default = null;
    };
    diskId = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      description = "The disk id, changing this will require a new installation";
      default = null;
    };
  };

  config = {
    clan.core.machine = {
      generateMachineId = false;
      generateDiskId = false;
      machineId = cfg.machineId;
      diskId = cfg.diskId;
    };
  };
}
