{
  clan-app,
  mkShell,
  ruff,
  webview-lib,
  self',
}:

mkShell {

  inputsFrom = [ self'.devShells.default ];

  inherit (clan-app) nativeBuildInputs propagatedBuildInputs;

  buildInputs = [
    (clan-app.pythonRuntime.withPackages (
      ps:
      with ps;
      [
        mypy
      ]
      ++ (clan-app.devshellPyDeps ps)
    ))
    ruff
  ] ++ clan-app.runtimeDeps;

  shellHook = ''
    export GIT_ROOT=$(git rev-parse --show-toplevel)
    export PKG_ROOT=$GIT_ROOT/pkgs/clan-app

    # Add current package to PYTHONPATH
    export PYTHONPATH="$PKG_ROOT''${PYTHONPATH:+:$PYTHONPATH:}"

    # Add clan-app command to PATH
    export PATH="$PKG_ROOT/bin":"$PATH"

    # Add clan-cli to the python path so that we can import it without building it in nix first
    export PYTHONPATH="$GIT_ROOT/pkgs/clan-cli":"$PYTHONPATH"

    export XDG_DATA_DIRS=$GSETTINGS_SCHEMAS_PATH:$XDG_DATA_DIRS

    export WEBVIEW_LIB_DIR=${webview-lib}/lib
    source $PKG_ROOT/.local.env
  '';
}
