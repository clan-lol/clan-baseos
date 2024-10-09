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
in
{
  inherit inventorySchema modulesSchema renderSchema;

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
