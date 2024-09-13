{
  config,
  pkgs,
  lib,
  ...
}:

let
  var = config.clan.core.vars.generators.machine-id.files.machineId or { };
in
{
  config = lib.mkMerge [
    (lib.mkIf ((var.machineId.value or null) != null) {
      assertions = [
        {
          assertion = lib.stringLength var.machineId.value == 32;
          message = "machineId must be exactly 32 characters long.";
        }
      ];
      boot.kernelParams = [
        ''systemd.machine_id=${var.machineId.value}''
      ];
      environment.etc."machine-id" = {
        text = var.machineId.value;
      };
    })
    {
      clan.core.vars.generators.machine-id = {
        files.machineId.secret = false;
        runtimeInputs = [
          pkgs.coreutils
          pkgs.bash
        ];
        script = ''
          uuid=$(bash ${../uuid4.sh})

          # Remove the hyphens from the UUID
          uuid_no_hyphens=$(echo -n "$uuid" | tr -d '-')

          echo -n "$uuid_no_hyphens" > "$out/machineId"
        '';
      };
    }
  ];
}
