# run these tests via `nix-unit ./test.nix`
{
  lib ? (import <nixpkgs> { }).lib,
  slib ? (import ./. { inherit lib; } { }),
}:
{
  # parseOption = import ./test_parseOption.nix { inherit lib slib; };
  parseOptions = import ./test_parseOptions.nix { inherit lib slib; };
}
