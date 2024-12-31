{ lib, config, ... }:
let
  directory = config.clan.core.settings.directory;
  machineName = config.clan.core.settings.machine.name;
  facterJson = "${directory}/machines/${machineName}/facter.json";
  hwConfig = "${directory}/machines/${machineName}/hardware-configuration.nix";
in
{
  facter.reportPath = lib.mkIf (builtins.pathExists facterJson) facterJson;
  warnings =
    lib.optionals
      (builtins.all builtins.pathExists [
        hwConfig
        facterJson
      ])
      [
        ''
          Duplicate hardware facts: '${hwConfig}' and '${facterJson}' exist.
          Using both is not recommended.

          It is recommended to use the hardware facts from '${facterJson}', please remove '${hwConfig}'.
        ''
      ];
}
