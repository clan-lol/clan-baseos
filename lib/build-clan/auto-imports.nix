{
  lib,
  self,
  ...
}:

let
  # Returns an attrset with inputs that have the attribute `clanModules`
  inputsWithClanModules = lib.filterAttrs (
    _name: value: builtins.hasAttr "clanModules" value
  ) self.inputs;

  flattenedClanModules = lib.foldl' (
    acc: input:
    lib.mkMerge [
      acc
      input.clanModules
    ]
  ) { } (lib.attrValues inputsWithClanModules);
in
{
  inventory.modules = flattenedClanModules;
}
