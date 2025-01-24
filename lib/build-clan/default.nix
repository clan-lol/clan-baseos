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
  directory ? null, # The directory containing the machines subdirectory # allows to include machine-specific modules i.e. machines.${name} = { ... }
  self ? null,
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
  evalUnchecked = import ./eval.nix {
    inherit
      lib
      nixpkgs
      clan-core
      ;
    inherit specialArgs;
    self = if self != null then self else directory;
  };

  # Doing `self ? lib.trace "please use self" directory`, doesn't work
  # as when both (directory and self) are set we get an infinite recursion error
  eval =
    if directory == null && self == null then
      throw "The buildClan function requires argument 'self' to be set"
    else if directory != null && self != null then
      throw "Both 'self' and 'directory' are set, please remove 'directory' in favor of the 'self' argument"
    else if directory != null then
      lib.warn "The 'directory' argument in buildClan has been deprecated in favor of the 'self' argument" evalUnchecked
    else
      evalUnchecked;
  rest = builtins.removeAttrs attrs [ "specialArgs" ];
in
eval {
  imports = [
    rest
    # implementation
    ./module.nix
    ./auto-imports.nix
  ];
}
