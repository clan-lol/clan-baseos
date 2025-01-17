{ self, ... }:
let
  nixFilter = import ./nix-filter.nix;
in
{
  flake.filter =
    {
      include ? [ ],
      exclude ? [ ],
    }:
    nixFilter.filter {
      inherit exclude;
      include = include ++ [
        "flake.nix"
      ];
      root = self;
    };
}
