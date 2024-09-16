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

      optionsFromModule =
        mName:
        let
          eval = self.lib.evalClanModules [ mName ];
        in
        if (eval.options.clan ? "${mName}") then eval.options.clan.${mName} else { };

      clanModuleSchemas = lib.mapAttrs (
        modulename: _: jsonLib.parseOptions (optionsFromModule modulename) { }
      ) clanModules;

      clanModuleFunctionSchemas = lib.mapAttrsFlatten (
        modulename: _:
        (self.lib.modules.getFrontmatter modulename)
        // {
          name = modulename;
          parameters = jsonLib.parseOptions (optionsFromModule modulename) { };
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
