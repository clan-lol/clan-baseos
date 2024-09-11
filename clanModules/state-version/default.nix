{ config, lib, ... }:
let
  var = config.clan.core.vars.generators.state-version.files.version or { };
in
{
  config = lib.mkMerge [
    (lib.mkIf ((var.value or null) != null) {
      system.stateVersion = lib.mkDefault (lib.removeSuffix "\n" var.value);
    })

    {
      clan.core.vars.generators.state-version = {
        files.version.secret = false;
        runtimeInputs = [ ];
        script = ''
          echo ${lib.versions.majorMinor lib.version} > $out/version
        '';
      };
    }
  ];
}
