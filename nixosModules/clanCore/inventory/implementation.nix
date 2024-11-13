{ config, ... }:
{
  config.assertions = builtins.attrValues (
    builtins.mapAttrs (_id: value: value // { inherit _id; }) config.clan.inventory.assertions
  );
}
