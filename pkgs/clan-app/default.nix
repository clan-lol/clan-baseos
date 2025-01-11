{
  runCommand,
  copyDesktopItems,
  clan-cli,
  makeDesktopItem,
  webview-ui,
  webview-lib,
  fontconfig,
  pythonRuntime,
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

  # Runtime binary dependencies required by the application
  runtimeDependencies = [

  ];

  pyDeps = ps: [
    ps.tkinter
  ];

  # Dependencies required for running tests
  pyTestDeps =
    ps:
    [
      # Testing framework
      ps.pytest
      ps.pytest-cov # Generate coverage reports
      ps.pytest-subprocess # fake the real subprocess behavior to make your tests more independent.
      ps.pytest-xdist # Run tests in parallel on multiple cores
      ps.pytest-timeout # Add timeouts to your tests
    ]
    ++ ps.pytest.propagatedBuildInputs;

  clan-cli-module = [
    (pythonRuntime.pkgs.toPythonModule (clan-cli.override { inherit pythonRuntime; }))
  ];

in
pythonRuntime.pkgs.buildPythonApplication {
  name = "clan-app";
  src = source;
  format = "pyproject";

  dontWrapGApps = true;
  preFixup = ''
    makeWrapperArgs+=(
      --set FONTCONFIG_FILE ${fontconfig.out}/etc/fonts/fonts.conf
      --set WEBUI_PATH "$out/${pythonRuntime.sitePackages}/clan_app/.webui"
      --set WEBVIEW_LIB_DIR "${webview-lib}/lib"
      # This prevents problems with mixed glibc versions that might occur when the
      # cli is called through a browser built against another glibc
      --unset LD_LIBRARY_PATH
      "''${gappsWrapperArgs[@]}"
    )
  '';

  # Deps needed only at build time
  nativeBuildInputs = [
    (pythonRuntime.withPackages (ps: [ ps.setuptools ]))
    copyDesktopItems
    fontconfig
  ];

  # The necessity of setting buildInputs and propagatedBuildInputs to the
  # same values for your Python package within Nix largely stems from ensuring
  # that all necessary dependencies are consistently available both
  # at build time and runtime,
  propagatedBuildInputs = [
    (pythonRuntime.withPackages (ps: clan-cli-module ++ (pyDeps ps)))
  ] ++ runtimeDependencies;

  # also re-expose dependencies so we test them in CI
  passthru = {
    tests = {
      clan-app-pytest =
        runCommand "clan-app-pytest"
          {
            buildInputs = runtimeDependencies ++ [
              (pythonRuntime.withPackages (ps: clan-cli-module ++ (pyTestDeps ps) ++ (pyDeps ps)))
              fontconfig
            ];
          }
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
            export WEBVIEW_LIB_DIR="${webview-lib}/lib"
            export NIX_STATE_DIR=$TMPDIR/nix IN_NIX_SANDBOX=1
            python -m pytest -s -m "not impure" ./tests
            touch $out
          '';
    };
  };

  # Additional pass-through attributes
  passthru.desktop-file = desktop-file;
  passthru.devshellPyDeps = ps: (pyTestDeps ps) ++ (pyDeps ps);
  passthru.pythonRuntime = pythonRuntime;

  postInstall = ''
    mkdir -p $out/${pythonRuntime.sitePackages}/clan_app/.webui
    cp -r ${webview-ui}/lib/node_modules/@clan/webview-ui/dist/* $out/${pythonRuntime.sitePackages}/clan_app/.webui
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
