{
  self,
  self',
  pkgs,
  lib,
  ...
}:
let
  includeDefaults = true;

  # { mName :: { roleName :: Options } }
  modulesRolesOptions = self.lib.evalClanModulesWithRoles self.clanModules;
  modulesSchema = lib.mapAttrs (
    _moduleName: rolesOptions:
    lib.mapAttrs (_roleName: options: jsonWithoutHeader.parseOptions options { }) rolesOptions
  ) modulesRolesOptions;

  jsonLib = self.lib.jsonschema { inherit includeDefaults; };

  jsonWithoutHeader = self.lib.jsonschema {
    inherit includeDefaults;
    header = { };
  };

  inventorySchema = jsonLib.parseModule (import ../build-inventory/interface.nix);

  renderSchema = pkgs.writers.writePython3Bin "render-schema" {
    flakeIgnore = [
      "F401"
      "E501"
    ];
  } ./render_schema.py;

  inventory-schema-abstract = pkgs.stdenv.mkDerivation {
    name = "inventory-schema-files";
    buildInputs = [ pkgs.cue ];
    src = ./.;
    buildPhase = ''
      export SCHEMA=${builtins.toFile "inventory-schema.json" (builtins.toJSON inventorySchema)}
      cp $SCHEMA schema.json
      # Also generate a CUE schema version that is derived from the JSON schema
      cue import -f -p compose -l '#Root:' schema.json
      mkdir $out
      cp schema.cue $out
      cp schema.json $out
    '';
  };
in
{
  inherit
    inventorySchema
    modulesSchema
    renderSchema
    inventory-schema-abstract
    ;

  # Inventory schema, with the modules schema added per role
  inventory =
    pkgs.runCommand "rendered"
      {
        buildInputs = [
          pkgs.python3
          self'.packages.clan-cli
        ];
      }
      ''
        export INVENTORY_SCHEMA_PATH=${builtins.toFile "inventory-schema.json" (builtins.toJSON inventorySchema)}
        export MODULES_SCHEMA_PATH=${builtins.toFile "modules-schema.json" (builtins.toJSON modulesSchema)}

        mkdir $out
        # The python script will place the schemas in the output directory
        exec python3 ${renderSchema}/bin/render-schema
      '';
}
