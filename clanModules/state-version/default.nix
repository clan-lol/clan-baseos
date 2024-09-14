{ config, lib, ... }:
let
  var = config.clan.core.vars.generators.state-version.files.version or { };
in
{
  config = lib.mkMerge [
    (lib.mkIf ((var.value or null) != null) {
      system.stateVersion = lib.mkDefault var.value;
    })

    {
      clan.core.vars.generators.state-version = {
        files.version.secret = false;
        runtimeInputs = [ ];
        script = ''
          echo -n ${lib.versions.majorMinor config.system.stateVersion} > $out/version
        '';
      };
    }
  ];
}
