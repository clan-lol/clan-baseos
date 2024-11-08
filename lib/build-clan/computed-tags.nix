{
  config,
  lib,
  ...
}:
{
  config.inventory = {
    tags = (
      { machines, ... }:
      {
        # Only compute the default value
        # The option MUST be defined in ./build-inventory/interface.nix
        all = lib.mkDefault (builtins.attrNames machines);
      }
    );
  };
  # Add the computed tags to machine tags for displaying them
  options.inventory = {
    machines = lib.mkOption {
      type = lib.types.attrsOf (
        lib.types.submodule (
          # 'name' is the machines attribute-name
          { name, ... }:
          {
            tags = builtins.attrNames (
              lib.filterAttrs (_t: tagMemers: builtins.elem name tagMemers) config.inventory.tags
            );
          }
        )
      );
    };
  };
}
