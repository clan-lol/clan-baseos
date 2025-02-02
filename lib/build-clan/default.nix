## WARNING: Do not add core logic here.
## This is only a wrapper such that buildClan can be called as a function.
## Add any logic to ./module.nix
{
  lib,
  nixpkgs,
  clan-core,
}:
{
  ## Inputs
  self ? null, # Reference to the current flake
  directory ? null, # the directory containing the machines subdirectory. Optional: can be used if the machines is not in the root of the flake
  # allows to include machine-specific modules i.e. machines.${name} = { ... }
  # A map from arch to pkgs, if specified this nixpkgs will be only imported once for each system.
  # This improves performance, but all nipxkgs.* options will be ignored.
  # deadnix: skip
  inventory ? { },
  ## Special inputs (not passed to the module system as config)
  specialArgs ? { }, # Extra arguments to pass to nixosSystem i.e. useful to make self available # A set containing clan meta: name :: string, icon :: string, description :: string
  ##
  ...
}@attrs:
let
  eval = import ./eval.nix {
    inherit
      lib
      nixpkgs
      clan-core
      ;
    inherit specialArgs;
    self =
      if self == null then
        lib.warn "The buildClan function requires argument 'self' to be set to the current flake" {
          inputs = { };
        }
      else
        self;
    directory = if directory == null then self else directory;
  };

  rest = builtins.removeAttrs attrs [ "specialArgs" ];
in
eval {
  imports = [
    rest
    # implementation
    ./module.nix
  ];
}
