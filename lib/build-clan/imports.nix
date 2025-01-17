{
  config,
  lib,
  ...
}:
##################################
#                                #
# Handle the "imports" directory #
#                                #
##################################

let
  inherit (config)
    directory
    ;

  # Check if the imports directory exists
  # If it does, check if the files in the directory are allowed
  importsDir =
    if builtins.pathExists "${directory}/imports" then
      (
        let
          allowedFiles = [
            "inventory"
          ];
          invalidImports = lib.filter (name: !(lib.elem name allowedFiles)) (
            builtins.attrNames (builtins.readDir "${directory}/imports")
          );
        in
        if invalidImports != [ ] then
          builtins.throw ''
            Invalid file imports/{${lib.concatStringsSep ", " invalidImports}}. 
            Allowed are imports/{${lib.concatStringsSep ", " allowedFiles}}
          ''
        else
          "${directory}/imports"
      )
    else
      "${directory}/imports";

  # Get the directory names in the inventory/imports directory
  inventoryImportNames =
    if builtins.pathExists "${importsDir}/inventory" then
      let
        inventoryEntries = builtins.readDir "${importsDir}/inventory";
        invalidFiles = builtins.attrNames (lib.filterAttrs (_: type: type == "regular") inventoryEntries);
      in
      if invalidFiles != [ ] then
        builtins.throw ''
          Invalid file(s) in imports/inventory/{${lib.concatStringsSep ", " invalidFiles}}
          Only directories are allowed.
        ''
      else
        builtins.attrNames (lib.filterAttrs (_: type: type == "directory") inventoryEntries)
    else
      [ ];

  # Check if the roles directory exists in each inventory import
  inventoryImportAttrsetWithCheck = lib.genAttrs inventoryImportNames (
    name:
    let
      rolesDir = "${directory}/imports/inventory/${name}/roles";
    in
    if builtins.pathExists rolesDir then
      rolesDir
    else
      builtins.throw "The module ${name} is not inventory compatible because the roles directory does not exist at ${rolesDir}"
  );
in
{
  inventory.modules = inventoryImportAttrsetWithCheck;
}
