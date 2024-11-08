{ inputs, ... }:
{
  imports = [
    inputs.clan.flakeModules.default
  ];
  clan = {
    specialArgs = {
      inherit inputs;
    };
  };
}
