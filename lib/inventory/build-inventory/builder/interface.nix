{ lib, ... }:
let
  inherit (lib) types mkOption;
  submodule = m: types.submoduleWith { modules = [ m ]; };

in
{
  options = {
    directory = mkOption {
      type = types.path;
    };
    inventory = mkOption {
      type = types.raw;
    };
    machines = mkOption {
      type = types.attrsOf (submodule {
        options = {
          compiledMachine = mkOption {
            type = types.raw;
          };
          compiledServices = mkOption {
            type = types.raw;
          };
          machineImports = mkOption {
            type = types.listOf types.raw;
          };
        };
      });
    };
  };
}
