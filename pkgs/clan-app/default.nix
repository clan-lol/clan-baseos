{
  python3,
  runCommand,
  setuptools,
  copyDesktopItems,
  pygobject3,
  wrapGAppsHook4,
  gtk4,
  adwaita-icon-theme,
  pygobject-stubs,
  gobject-introspection,
  clan-cli,
  makeDesktopItem,
  libadwaita,
  webkitgtk_6_0,
  pytest, # Testing framework
  pytest-cov, # Generate coverage reports
  pytest-subprocess, # fake the real subprocess behavior to make your tests more independent.
  pytest-xdist, # Run tests in parallel on multiple cores
  pytest-timeout, # Add timeouts to your tests
  webview-ui,
  webview-lib,
  fontconfig,
}:
let
  source = ./.;
  desktop-file = makeDesktopItem {
    name = "org.clan.app";
    exec = "clan-app %u";
    icon = "clan-white";
    desktopName = "Clan App";
    startupWMClass = "clan";
    mimeTypes = [ "x-scheme-handler/clan" ];
  };

  # Dependencies that are directly used in the project but nor from internal python packages
  externalPythonDeps = [
    pygobject3
    pygobject-stubs
    gtk4
    libadwaita
    webkitgtk_6_0
    adwaita-icon-theme

  ];

  # Deps including python packages from the local project
  allPythonDeps = [ (python3.pkgs.toPythonModule clan-cli) ] ++ externalPythonDeps;

  # Runtime binary dependencies required by the application
  runtimeDependencies = [
    webview-lib
  ];

  # Dependencies required for running tests
  externalTestDeps =
    externalPythonDeps
    ++ runtimeDependencies
    ++ [
      pytest # Testing framework
      pytest-cov # Generate coverage reports
      pytest-subprocess # fake the real subprocess behavior to make your tests more independent.
      pytest-xdist # Run tests in parallel on multiple cores
      pytest-timeout # Add timeouts to your tests
    ];

  # Dependencies required for running tests
  testDependencies = runtimeDependencies ++ allPythonDeps ++ externalTestDeps;

  # Setup Python environment with all dependencies for running tests
  pythonWithTestDeps = python3.withPackages (_ps: testDependencies);
in
python3.pkgs.buildPythonApplication rec {
  name = "clan-app";
  src = source;
  format = "pyproject";

  dontWrapGApps = true;
  preFixup = ''
    makeWrapperArgs+=(
      --set FONTCONFIG_FILE ${fontconfig.out}/etc/fonts/fonts.conf
      --set WEBUI_PATH "$out/${python3.sitePackages}/clan_app/.webui"
      --set WEBVIEW_LIB_DIR "${webview-lib}/lib"
      # This prevents problems with mixed glibc versions that might occur when the
      # cli is called through a browser built against another glibc
      --unset LD_LIBRARY_PATH
      "''${gappsWrapperArgs[@]}"
    )
  '';

  # Deps needed only at build time
  nativeBuildInputs = [
    setuptools
    copyDesktopItems
    wrapGAppsHook4

    gobject-introspection
  ];

  # The necessity of setting buildInputs and propagatedBuildInputs to the
  # same values for your Python package within Nix largely stems from ensuring
  # that all necessary dependencies are consistently available both
  # at build time and runtime,
  buildInputs = allPythonDeps ++ runtimeDependencies;
  propagatedBuildInputs =
    allPythonDeps
    ++ runtimeDependencies
    ++ [

      # TODO: see postFixup clan-cli/default.nix:L188
      clan-cli.propagatedBuildInputs
    ];

  # also re-expose dependencies so we test them in CI
  passthru = {
    tests = {
      clan-app-pytest =
        runCommand "clan-app-pytest" { inherit buildInputs propagatedBuildInputs nativeBuildInputs; }
          ''
            cp -r ${source} ./src
            chmod +w -R ./src
            cd ./src

            export FONTCONFIG_FILE=${fontconfig.out}/etc/fonts/fonts.conf
            export FONTCONFIG_PATH=${fontconfig.out}/etc/fonts

            mkdir -p .home/.local/share/fonts
            export HOME=.home

            fc-cache --verbose
            # > fc-cache succeeded

            echo "Loaded the following fonts ..."
            fc-list

            echo "STARTING ..."
            export NIX_STATE_DIR=$TMPDIR/nix IN_NIX_SANDBOX=1
            ${pythonWithTestDeps}/bin/python -m pytest -s -m "not impure" ./tests
            touch $out
          '';
    };
  };

  # Additional pass-through attributes
  passthru.desktop-file = desktop-file;
  passthru.externalPythonDeps = externalPythonDeps;
  passthru.externalTestDeps = externalTestDeps;
  passthru.runtimeDependencies = runtimeDependencies;
  passthru.testDependencies = testDependencies;

  postInstall = ''
    mkdir -p $out/${python3.sitePackages}/clan_app/.webui
    cp -r ${webview-ui}/lib/node_modules/@clan/webview-ui/dist/* $out/${python3.sitePackages}/clan_app/.webui
    mkdir -p $out/share/icons/hicolor
    cp -r ./clan_app/assets/white-favicons/* $out/share/icons/hicolor
  '';

  # Don't leak python packages into a devshell.
  # It can be very confusing if you `nix run` than load the cli from the devshell instead.
  postFixup = ''
    rm $out/nix-support/propagated-build-inputs
  '';
  checkPhase = ''
    export FONTCONFIG_FILE=${fontconfig.out}/etc/fonts/fonts.conf
    export FONTCONFIG_PATH=${fontconfig.out}/etc/fonts

    mkdir -p .home/.local/share/fonts
    export HOME=.home

    fc-cache --verbose
    # > fc-cache succeeded

    echo "Loaded the following fonts ..."
    fc-list

    PYTHONPATH= $out/bin/clan-app --help
  '';
  desktopItems = [ desktop-file ];
}
