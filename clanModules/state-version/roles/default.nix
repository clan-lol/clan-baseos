{ config, lib, ... }:
let
  var = config.clan.core.vars.generators.state-version.files.version or { };
in
{
  system.stateVersion = lib.mkDefault var.value;

  clan.core.vars.generators.state-version = {
    files.version = {
      secret = false;
      value = lib.mkDefault lib.version;
    };
    runtimeInputs = [ ];
    script = ''
      echo -n ${lib.versions.majorMinor config.system.stateVersion} > $out/version
    '';
  };
}
