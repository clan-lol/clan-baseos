{ ... }:
{
  perSystem =
    {
      config,
      pkgs,
      lib,
      system,
      self',
      ...
    }:
    if lib.elem system lib.platforms.darwin then
      { }
    else
      {
        devShells.clan-app = pkgs.callPackage ./shell.nix {
          inherit (config.packages) clan-app webview-lib;
          inherit self';
        };
        packages.clan-app = pkgs.python3.pkgs.callPackage ./default.nix {
          inherit (config.packages) clan-cli webview-ui webview-lib;
        };

        checks = config.packages.clan-app.tests;
      };
}
