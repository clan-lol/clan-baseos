{ lib, self }:
let
  # Trim the .nix extension from a filename
  trimExtension = name: builtins.substring 0 (builtins.stringLength name - 4) name;

  jsonWithoutHeader = self.lib.jsonschema {
    includeDefaults = true;
    header = { };
  };

  getModulesSchema =
    modules:
    lib.mapAttrs (
      _moduleName: rolesOptions:
      lib.mapAttrs (_roleName: options: jsonWithoutHeader.parseOptions options { }) rolesOptions
    ) (self.lib.evalClanModulesWithRoles modules);

  evalFrontmatter =
    {
      moduleName,
      instanceName,
      resolvedRoles,
      allModules,
    }:
    lib.evalModules {
      specialArgs = {
        inherit moduleName resolvedRoles instanceName;
        allRoles = getRoles allModules moduleName;
      };
      modules = [
        (getFrontmatter allModules.${moduleName} moduleName)
        ./interface.nix
      ];
    };

  # For Documentation purposes only
  frontmatterOptions =
    (lib.evalModules {
      specialArgs = {
        moduleName = "{moduleName}";
        allRoles = [ "{roleName}" ];
      };
      modules = [
        ./interface.nix
      ];
    }).options;

  getRoles =
    allModules: serviceName:
    lib.mapAttrsToList (name: _value: trimExtension name) (
      lib.filterAttrs (name: type: type == "regular" && lib.hasSuffix ".nix" name) (
        builtins.readDir (
          if allModules ? ${serviceName} then
            allModules.${serviceName} + "/roles"
          else
            throw "ClanModule not found: '${serviceName}'. Make sure the module is added in the 'clanModules' attribute of clan-core."
        )
      )
    );

  checkConstraints = args: (evalFrontmatter args).config.constraints.assertions;

  getReadme =
    modulepath: modulename:
    let
      readme = modulepath + "/README.md";
      readmeContents =
        if (builtins.pathExists readme) then
          (builtins.readFile readme)
        else
          throw "No README.md found for module ${modulename}";
    in
    readmeContents;

  getFrontmatter =
    modulepath: modulename:
    let
      content = getReadme modulepath modulename;
      parts = lib.splitString "---" content;
      # Partition the parts into the first part (the readme content) and the rest (the metadata)
      parsed = builtins.partition ({ index, ... }: if index >= 2 then false else true) (
        lib.filter ({ index, ... }: index != 0) (lib.imap0 (index: part: { inherit index part; }) parts)
      );
      meta = builtins.fromTOML (builtins.head parsed.right).part;
    in
    if (builtins.length parts >= 3) then
      meta
    else
      throw ''
        TOML Frontmatter not found in README.md for module ${modulename}

        Please add the following to the top of your README.md:

        ---
        description = "Your description here"
        categories = [ "Your categories here" ]
        features = [ "inventory" ]
        ---
        ...rest of your README.md...
      '';
in
{
  inherit
    frontmatterOptions
    getModulesSchema
    getFrontmatter

    checkConstraints
    getRoles
    ;
}
