{
  lib,
  nixpkgs,
  clan-core,
  self,
  directory ? null,
  specialArgs ? { },
}:
# Returns a function that takes self, which should point to the directory of the flake
module:
(lib.evalModules {
  specialArgs = {
    inherit self clan-core nixpkgs;
  };
  modules = [
    ./interface.nix
    module
    {
      inherit specialArgs;
      directory = lib.mkIf (directory != null) directory;
    }
  ];
}).config
