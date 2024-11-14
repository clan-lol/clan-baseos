{ ... }:
{
  perSystem =
    {
      pkgs,
      config,
      self',
      ...
    }:
    {
      packages.webview-ui = pkgs.buildNpmPackage {
        pname = "clan-webview-ui";
        version = "0.0.1";

        src = ./app;

        npmDeps = pkgs.importNpmLock { npmRoot = ./app; };
        npmConfigHook = pkgs.importNpmLock.npmConfigHook;

        preBuild = ''
          mkdir -p api
          cp -r ${config.packages.clan-ts-api}/* api
          cp -r ${pkgs.texlivePackages.archivo.tex}/fonts/opentype/public/archivo ".fonts"
        '';
      };
      devShells.webview-ui = pkgs.mkShell {
        inputsFrom = [
          config.packages.webview-ui
          self'.devShells.default
        ];
        shellHook = ''
          export GIT_ROOT="$(git rev-parse --show-toplevel)"
          export PKG_ROOT="$GIT_ROOT/pkgs/webview-ui"
          export NODE_PATH="$PKG_ROOT/app/node_modules"
          export PATH="$NODE_PATH/.bin:$PATH"

          cp -r ${pkgs.texlivePackages.archivo.tex}/fonts/opentype/public/archivo "$PKG_ROOT/app/.fonts"

          # Define the yellow color code
          YELLOW='\033[1;33m'
          # Define the reset color code
          NC='\033[0m'

          # Check if the directory does not exist
          if [ ! -d "$PKG_ROOT/app/node_modules" ]; then
            echo -e "$YELLOW The directory $PKG_ROOT/app/node_modules does not exist.$NC"
            echo -e "$YELLOW Please run 'npm install' in the app directory.$NC"
            echo -e "$YELLOW This will install the necessary dependencies.$NC"
            echo -e "$YELLOW To serve the webview run 'vite'.$NC"
          else
            echo "The directory $PKG_ROOT/app/node_modules exists."
          fi


          mkdir -p ./app/api
          cp -r ${config.packages.clan-ts-api}/* app/api
          chmod -R +w app/api
        '';
      };
    };
}
