{ inputs, ... }:
{
  imports = [
    inputs.clan.flakeModules.default
  ];
  clan = {
    meta.name = "__CHANGE_ME__";
    specialArgs = {
      inherit inputs;
    };
  };
}
