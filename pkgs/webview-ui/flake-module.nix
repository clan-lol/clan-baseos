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
      packages.fonts =
        let
          # 400 -> Regular
          archivoRegular = pkgs.fetchurl {
            url = "https://github.com/Omnibus-Type/Archivo/raw/b5d63988ce19d044d3e10362de730af00526b672/fonts/webfonts/ArchivoSemiCondensed-Regular.woff2";
            hash = "sha256-3PeB6tMpbYxR9JFyQ+yjpM7bAvZIjcJ4eBiHr9iV5p4=";
          };
          # 500 -> Medium
          archivoMedium = pkgs.fetchurl {
            url = "https://github.com/Omnibus-Type/Archivo/raw/b5d63988ce19d044d3e10362de730af00526b672/fonts/webfonts/ArchivoSemiCondensed-Medium.woff2";
            hash = "sha256-IKaY3YhpmjMaIVUpwKRLd6eFiIihBoAP99I/pwmyll8=";
          };
          # 600 -> SemiBold
          archivoSemiBold = pkgs.fetchurl {
            url = "https://github.com/Omnibus-Type/Archivo/raw/b5d63988ce19d044d3e10362de730af00526b672/fonts/webfonts/ArchivoSemiCondensed-SemiBold.woff2";
            hash = "sha256-fOE+b+UeTRoj+sDdUWR1pPCZVn0ABy6FEDDmXrOA4LY=";
          };
        in
        pkgs.runCommand "" { } ''
          mkdir -p $out
          cp ${archivoRegular} $out/ArchivoSemiCondensed-Regular.woff2
          cp ${archivoMedium} $out/ArchivoSemiCondensed-Medium.woff2
          cp ${archivoSemiBold} $out/ArchivoSemiCondensed-SemiBold.woff2
        '';
      packages.webview-ui = pkgs.buildNpmPackage {
        pname = "clan-webview-ui";
        version = "0.0.1";

        src = ./app;

        npmDeps = pkgs.importNpmLock { npmRoot = ./app; };
        npmConfigHook = pkgs.importNpmLock.npmConfigHook;

        preBuild = ''
          mkdir -p api
          cp -r ${config.packages.clan-ts-api}/* api
          cp -r ${self'.packages.fonts} ".fonts"
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

          cp -r ${self'.packages.fonts} "$PKG_ROOT/app/.fonts"
          chmod -R +w "$PKG_ROOT/app/.fonts"

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
