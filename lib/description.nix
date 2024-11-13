{ clan-core, lib }:
let
  getRoles =
    modulePath:
    let
      rolesDir = modulePath + "/roles";
    in
    if builtins.pathExists rolesDir then
      lib.pipe rolesDir [
        builtins.readDir
        (lib.filterAttrs (_n: v: v == "regular"))
        lib.attrNames
        (lib.filter (fileName: lib.hasSuffix ".nix" fileName))
        (map (fileName: lib.removeSuffix ".nix" fileName))
      ]
    else
      [ ];

  getConstraints =
    modulename:
    let
      eval = lib.evalModules {
        specialArgs = {
          allRoles = getRoles clan-core.clanModules.${modulename};
        };
        modules = [
          ./constraints/interface.nix
          (getFrontmatter modulename).constraints
        ];
      };
    in
    eval.config.roles;

  checkConstraints =
    { moduleName, resolvedRoles }:
    let
      eval = lib.evalModules {
        specialArgs = {
          inherit moduleName;
          allRoles = getRoles clan-core.clanModules.${moduleName};
          resolvedRoles = {
            controller = {
              machines = [ "test-inventory-machine" ];
            };
            moon = {
              machines = [ ];
            };
            peer = {
              machines = [ ];
            };
          };
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
    getRoles
    getConstraints
    checkConstraints
    ;
}
