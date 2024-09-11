{ config, lib, ... }:
{
  system.stateVersion = config.clan.core.vars.generators.state-version.files.version.value;

  clan.core.vars.generators.state-version = {
    files.version.secret = false;
    runtimeInputs = [ ];
    script = ''
      echo ${lib.versions.majorMinor lib.version} > $out/version
    '';
  };
}
