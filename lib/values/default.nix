{
  lib ? import <nixpkgs/lib>,
}:
let
  filterOptions = lib.filterAttrs (
    name: _:
    !builtins.elem name [
      "_module"
      "_freeformOptions"
    ]
  );

  getPrios =
    {
      options,
    }:
    let
      filteredOptions = filterOptions options;
    in
    lib.mapAttrs (
      _: opt:
      let
        prio = {
          __prio = opt.highestPrio;
        };
        subOptions = opt.type.getSubOptions opt.loc;

        attrDefinitions = (lib.modules.mergeAttrDefinitionsWithPrio opt);
        zipDefs = builtins.zipAttrsWith (_ns: vs: vs);
        defs = zipDefs opt.definitions;

        prioPerValue =
          { type, defs }:
          lib.mapAttrs (
            attrName: prioSet:
            let
              # Evaluate the submodule
              options = filterOptions subOptions;
              modules = (
                [
                  { inherit options; }
                ]
                ++ map (config: { inherit config; }) defs.${attrName}
              );
              submoduleEval = lib.evalModules {
                inherit modules;
              };
            in
            (lib.optionalAttrs (prioSet ? highestPrio) {
              __prio = prioSet.highestPrio;
              # inherit defs options;
            })
            // (
              if type.nestedTypes.elemType.name == "submodule" then
                getPrios { options = submoduleEval.options; }
              else
                # Nested attrsOf
                (lib.optionalAttrs (type.nestedTypes.elemType.name == "attrsOf") (
                  prioPerValue {
                    type = type.nestedTypes.elemType;
                    defs = zipDefs defs.${attrName};
                  } prioSet.value
                ))
            )
          );

        attributePrios = prioPerValue {
          type = opt.type;
          inherit defs;
        } attrDefinitions;
      in
      if opt ? type && opt.type.name == "submodule" then
        prio // (getPrios { options = subOptions; })
      else if opt ? type && opt.type.name == "attrsOf" then
        #   prio // attributePrios
        # else if
        #   opt ? type && opt.type.name == "attrsOf" && opt.type.nestedTypes.elemType.name == "attrsOf"
        # then
        #   prio // attributePrios
        # else if opt ? type && opt.type.name == "attrsOf" then
        prio // attributePrios
      else if opt ? type && opt._type == "option" then
        prio
      else
        getPrios { options = opt; }
    ) filteredOptions;
in
{
  inherit getPrios;
}
