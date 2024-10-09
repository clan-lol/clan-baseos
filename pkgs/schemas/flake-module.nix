{ self, ... }:
{
  perSystem =
    { pkgs, lib, ... }:
    let
      clanModules = self.clanModules;

      jsonLib = self.lib.jsonschema { };

      # Uncomment if you only want one module to be available
      # clanModules = {
      #   borgbackup = self.clanModules.borgbackup;
      # };

      optionsFromModule = name: module: (self.lib.evalClanModules [ module ]).options.clan.${name} or { };

      clanModuleSchemas = lib.mapAttrs (
        name: module: jsonLib.parseOptions (optionsFromModule name module) { }
      ) clanModules;

      clanModuleFunctionSchemas = lib.attrsets.mapAttrsToList (
        modulename: module:
        (self.lib.modules.getFrontmatter modulename)
        // {
          name = modulename;
          parameters = jsonLib.parseOptions (optionsFromModule modulename module) { };
        }
      ) clanModules;
    in
    rec {
      checks = {
        module-schema = pkgs.runCommand "schema-checks" { } ''
          ${pkgs.check-jsonschema}/bin/check-jsonschema \
            --check-metaschema ${packages.module-schema}
          touch $out
        '';
      };

      packages = {
        module-schema = pkgs.runCommand "jsonschema" { } ''
          MSCHEMA=${builtins.toFile "module-schemas.json" (builtins.toJSON clanModuleSchemas)}
          cp "$MSCHEMA" $out
        '';

        function-schema = pkgs.runCommand "function-schema" { } ''
          FSCHEMA=${builtins.toFile "function-schemas.json" (builtins.toJSON clanModuleFunctionSchemas)}
          cp "$FSCHEMA" $out
        '';
      };
    };
}
