{
  config,
  pkgs,
  lib,
  ...
}:

let
  cfg = config.clan.core.machine;
  facts = config.clan.core.facts.services.diskId.public or { };
in
{
  options.clan.core.machine = {
    diskId = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      description = "The disk id";
    };
    generateDiskId = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Generate a new disk id";
    };
  };

  config = lib.mkMerge [
    (lib.mkIf ((facts.diskId.value or null) != null) {
      clan.core.machine.diskId = lib.mkDefault facts.diskId.value;
    })
    (lib.mkIf cfg.generateDiskId {
      clan.core.facts.services.diskId = {
        public.diskId = { };
        generator.path = [
          pkgs.coreutils
          pkgs.bash
        ];
        generator.script = ''
          uuid=$(bash ${./uuid4.sh})

          # Remove the hyphens from the UUID
          uuid_no_hyphens=$(echo -n "$uuid" | tr -d '-')

          echo -n "$uuid_no_hyphens" > "$facts/diskId"
        '';
      };
    })
  ];
}
