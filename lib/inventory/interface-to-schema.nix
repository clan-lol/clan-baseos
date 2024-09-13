{ lib, self, ... }:
{
  includeDefaults ? true,
}:
let
  optionsFromModule =
    mName:
    let
      eval = self.lib.evalClanModules [ mName ];
    in
    if (eval.options.clan ? "${mName}") then eval.options.clan.${mName} else { };

  modulesSchema = lib.mapAttrs (
    moduleName: _: jsonLib'.parseOptions (optionsFromModule moduleName) { }
  ) self.clanModules;

  jsonLib = self.lib.jsonschema { inherit includeDefaults; };
  jsonLib' = self.lib.jsonschema {
    inherit includeDefaults;
    header = { };
  };
  inventorySchema = jsonLib.parseModule (import ./build-inventory/interface.nix);

  getRoles =
    modulePath:
    let
      rolesDir = "${modulePath}/roles";
    in
    if builtins.pathExists rolesDir then
      lib.pipe rolesDir [
        builtins.readDir
        (lib.filterAttrs (_n: v: v == "regular"))
        lib.attrNames
        (map (fileName: lib.removeSuffix ".nix" fileName))
      ]
    else
      null;

  # The actual schema for the inventory
  # !!! We cannot import the module into the interface.nix, because it would cause evaluation overhead.
  # Modifies:
  # - service.<serviceName>.<instanceName>.config = moduleSchema
  # - service.<serviceName>.<instanceName>.machine.<machineName>.config = moduleSchema
  # - service.<serviceName>.<instanceName>.roles = acutalRoles

  schema =
    let
      moduleToService = moduleName: moduleSchema: {
        type = "object";
        additionalProperties = {
          type = "object";
          additionalProperties = false;
          properties = {
            meta = {
              title = "service-meta";
            } // inventorySchema.properties.services.additionalProperties.additionalProperties.properties.meta;

            config = {
              title = "${moduleName}-config";
              default = { };
            } // moduleSchema;
            roles = {
              type = "object";
              additionalProperties = false;
              required = [ ];
              properties = lib.listToAttrs (
                map (role: {
                  name = role;
                  value =
                    lib.recursiveUpdate
                      inventorySchema.properties.services.additionalProperties.additionalProperties.properties.roles.additionalProperties
                      {
                        properties.config = {
                          title = "${moduleName}-config";
                          default = { };
                        } // moduleSchema;
                      };
                }) (rolesOf moduleName)
              );
            };
            machines =
              lib.recursiveUpdate
                inventorySchema.properties.services.additionalProperties.additionalProperties.properties.machines
                {
                  additionalProperties.properties.config = {
                    title = "${moduleName}-config";
                    default = { };
                  } // moduleSchema;
                };
          };
        };
      };

      rolesOf =
        moduleName:
        let
          roles = getRoles self.clanModules.${moduleName};
        in
        if roles == null then [ "default" ] else roles;
      moduleServices = lib.mapAttrs moduleToService (
        lib.filterAttrs (n: _v: rolesOf n != [ ]) modulesSchema
      );
    in
    inventorySchema
    // {
      properties = inventorySchema.properties // {
        services = {
          type = "object";
          additionalProperties = false;
          properties = moduleServices;
        };
      };
    };
in
{
  /*
    The abstract inventory without the exact schema for each module filled

    InventorySchema<T extends Any> :: {
      serviceConfig :: dict[str, T];
    }
  */
  abstractSchema = inventorySchema;
  /*
    The inventory with each module schema filled.

    InventorySchema<T extends ModuleSchema> :: {
      ${serviceConfig} :: T; # <- each concrete module name is filled
    }
  */
  schemaWithModules = schema;
}
