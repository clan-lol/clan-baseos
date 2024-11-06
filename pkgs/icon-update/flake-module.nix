{ ... }:
{
  perSystem =
    {
      pkgs,
      system,
      lib,
      ...
    }:
    lib.optionalAttrs (system == "x86_64-linux") {
      packages.icon-update = pkgs.callPackage ./default.nix { };

      devShells.icon-update = pkgs.callPackage ./shell.nix { };
    };
}
