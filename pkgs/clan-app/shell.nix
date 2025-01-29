{
  gsettings-desktop-schemas,
  clan-app,
  mkShell,
  ruff,
  gtk4,
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

    export XDG_DATA_DIRS=${gtk4}/share/gsettings-schemas/gtk4-4.14.4:$XDG_DATA_DIRS
    export XDG_DATA_DIRS=${gsettings-desktop-schemas}/share/gsettings-schemas/gsettings-desktop-schemas-46.0:$XDG_DATA_DIRS

    export WEBVIEW_LIB_DIR=${webview-lib}/lib
    source $PKG_ROOT/.local.env
  '';
}
