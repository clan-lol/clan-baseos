_: {
  perSystem =
    {
      pkgs,
      inputs',
      ...
    }:
    {
      devShells = {
        default = pkgs.mkShellNoCC {
          packages = [
            inputs'.clan.packages.default
          ];
        };
      };
    };
}
