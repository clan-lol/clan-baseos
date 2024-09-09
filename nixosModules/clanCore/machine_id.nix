{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.clan.core.machine;
  facts = config.clan.core.facts.services.machineId.public or { };
in
{
  options.clan.core.machine = {
    machineId = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "A machine id based on the UUID v4 format";
    };
    generateMachineId = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Generate a new machine id";
    };
  };

  config = lib.mkMerge [
    (lib.mkIf (cfg.machineId != null) {
      assertions = [
        {
          assertion = lib.stringLength cfg.machineId == 32;
          message = "machineId must be exactly 32 characters long.";
        }
      ];
      boot.kernelParams = [
        ''systemd.machine_id=${cfg.machineId}''
      ];
    })
    (lib.mkIf ((facts.machineId.value or null) != null) {
      clan.core.machine.machineId = lib.mkDefault facts.machineId.value;
    })
    (lib.mkIf cfg.generateMachineId {
      clan.core.facts.services.machineId = {
        public.machineId = { };
        generator.path = [
          pkgs.coreutils
          pkgs.bash
        ];
        generator.script = ''
          uuid=$(bash ${./uuid4.sh})

          # Remove the hyphens from the UUID
          uuid_no_hyphens=$(echo -n "$uuid" | tr -d '-')

          echo -n "$uuid_no_hyphens" > "$facts/machineId"
        '';
      };
    })
  ];
}
