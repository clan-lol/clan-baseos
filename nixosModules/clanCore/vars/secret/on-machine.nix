{
  config,
  lib,
  pkgs,
  ...
}:
let
  sortedGenerators = lib.toposort (a: b: builtins.elem a.name b.dependencies) (
    lib.attrValues config.clan.core.vars.generators
  );
  generateSecrets = ''
    ${lib.concatStringsSep "\n" (_gen: ''
      v
    '') sortedGenerators}
  '';
in
{
  config = lib.mkIf (config.clan.core.vars.settings.secretStore == "on-machine") {
    environment.systemPackages = [
      (pkgs.writeShellApplication {
        text = generateSecrets;
      })
    ];
  };
}
