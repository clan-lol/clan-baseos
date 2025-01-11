{ ... }:
{
  perSystem =
    {
      config,
      pkgs,
      self',
      ...
    }:
    {
      devShells.clan-app = pkgs.callPackage ./shell.nix {
        inherit (config.packages) clan-app webview-lib;
        inherit self';
      };
      packages.clan-app = pkgs.callPackage ./default.nix {
        inherit (config.packages) clan-cli webview-ui webview-lib;
        pythonRuntime = pkgs.python3;
      };

      checks = config.packages.clan-app.tests;
    };
}
