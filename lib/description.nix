{ clan-core, lib }:
let
  trimExtension = name: builtins.substring 0 (builtins.stringLength name - 4) name;

  getRoles' =
    serviceName:
    lib.mapAttrsToList (name: _value: trimExtension name) (
      lib.filterAttrs (name: type: type == "regular" && lib.hasSuffix ".nix" name) (
        builtins.readDir (
          if clan-core.clanModules ? ${serviceName} then
            clan-core.clanModules.${serviceName} + "/roles"
          else
            throw "ClanModule not found: '${serviceName}'. Make sure the module is added in the 'clanModules' attribute of clan-core."
        )
      )
    );

  getConstraints =
    modulename:
    let
      eval = lib.evalModules {
        specialArgs = {
          allRoles = getRoles' modulename;
        };
        modules = [
          ./constraints/interface.nix
          (getFrontmatter modulename).constraints
        ];
      };
    in
    eval.config.roles;

  checkConstraints =
    {
      moduleName,
      resolvedRoles,
      instanceNames,
      instanceName,
    }:
    let
      eval = lib.evalModules {
        specialArgs = {
          inherit
            moduleName
            instanceNames
            instanceName
            resolvedRoles
            ;
          allRoles = getRoles' moduleName;
        };
        modules = [
          ./constraints/default.nix
          ((getFrontmatter moduleName).constraints or { })
        ];
      };
    in
    eval.config.assertions;

  getReadme =
    modulename:
    let
      readme = "${clan-core}/clanModules/${modulename}/README.md";
      readmeContents =
        if (builtins.pathExists readme) then
          (builtins.readFile readme)
        else
          throw "No README.md found for module ${modulename}";
    in
    readmeContents;

  getFrontmatter =
    modulename:
    let
      content = getReadme modulename;
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
    getFrontmatter
    getReadme
    getRoles'
    getConstraints
    checkConstraints
    ;
}
