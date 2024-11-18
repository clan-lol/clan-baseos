{
  clan-core,
  pkgs,
  module-docs,
  clan-cli-docs,
  asciinema-player-js,
  asciinema-player-css,
  roboto,
  fira-code,
  ...
}:
let
  uml-c4 = pkgs.python3Packages.plantuml-markdown.override { plantuml = pkgs.plantuml-c4; };
in
pkgs.stdenv.mkDerivation {
  name = "clan-documentation";

  # Points to repository root.
  # so that we can access directories outside of docs to include code snippets
  src = clan-core;

  nativeBuildInputs =
    [
      pkgs.python3
      uml-c4
    ]
    ++ (with pkgs.python3Packages; [
      mkdocs
      mkdocs-material
      mkdocs-macros
    ]);
  configurePhase = ''
    pushd docs

    mkdir -p ./site/reference/cli
    cp -af ${module-docs}/* ./site/reference/
    cp -af ${clan-cli-docs}/* ./site/reference/cli/

    mkdir -p ./site/static/asciinema-player
    ln -snf ${asciinema-player-js} ./site/static/asciinema-player/asciinema-player.min.js
    ln -snf ${asciinema-player-css} ./site/static/asciinema-player/asciinema-player.css

    # Link to fonts
    ln -snf ${roboto}/share/fonts/truetype/Roboto-Regular.ttf ./site/static/
    ln -snf ${fira-code}/share/fonts/truetype/FiraCode-VF.ttf ./site/static/

    # Copy icons into place
    cp -af ../pkgs/webview-ui/app/icons ./site/static/
  '';

  buildPhase = ''
    mkdocs build --strict
    ls -la .
  '';

  installPhase = ''
    cp -a out/ $out/
  '';
}
