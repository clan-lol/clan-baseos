{
  # callPackage args
  gnupg,
  installShellFiles,
  lib,
  nix,
  pkgs,
  runCommand,
  stdenv,
  nixVersions,
  # custom args
  clan-core-path,
  nixpkgs,
  includedRuntimeDeps,
  inventory-schema-abstract,
  classgen,
  pythonRuntime,
}:
let
  pyDeps = ps: [
    ps.argcomplete # Enables shell completions
  ];
  devDeps = ps: [
    ps.ipython
  ];
  pyTestDeps =
    ps:
    [
      ps.pytest
      ps.pytest-cov
      ps.pytest-subprocess
      ps.pytest-xdist
      ps.pytest-timeout
    ]
    ++ (pyDeps ps);
  pythonRuntimeWithDeps = pythonRuntime.withPackages (ps: pyDeps ps);

  # load nixpkgs runtime dependencies from a json file
  # This file represents an allow list at the same time that is checked by the run_cmd
  #   implementation in nix.py
  allDependencies = lib.importJSON ./clan_cli/nix/allowed-programs.json;
  generateRuntimeDependenciesMap =
    deps:
    lib.filterAttrs (_: pkg: !pkg.meta.unsupported or false) (lib.genAttrs deps (name: pkgs.${name}));
  testRuntimeDependenciesMap = generateRuntimeDependenciesMap allDependencies;
  testRuntimeDependencies = lib.attrValues testRuntimeDependenciesMap;
  bundledRuntimeDependenciesMap = generateRuntimeDependenciesMap includedRuntimeDeps;
  bundledRuntimeDependencies = lib.attrValues bundledRuntimeDependenciesMap;

  testDependencies = testRuntimeDependencies ++ [
    gnupg
    stdenv.cc # Compiler used for certain native extensions
    (pythonRuntime.withPackages (ps: (pyTestDeps ps) ++ (pyDeps ps)))
  ];

  source = runCommand "clan-cli-source" { } ''
    cp -r ${./.} $out
    chmod -R +w $out
    ln -sf ${nixpkgs'} $out/clan_cli/nixpkgs
    cp -r ${../../templates} $out/clan_cli/templates

    ${classgen}/bin/classgen ${inventory-schema-abstract}/schema.json $out/clan_cli/inventory/classes.py --stop-at "Service"
  '';

  # Create a custom nixpkgs for use within the project
  nixpkgs' =
    runCommand "nixpkgs"
      {
        nativeBuildInputs = [
          # old nix version doesn't support --flake flag
          (if lib.versionAtLeast nix.version "2.24" then nix else nixVersions.latest)
        ];
      }
      ''
        mkdir $out
        cat > $out/flake.nix << EOF
        {
          description = "dependencies for the clan-cli";

          inputs = {
            nixpkgs.url = "path://${nixpkgs}";
          };

          outputs = _inputs: { };
        }
        EOF
        ln -sf ${nixpkgs} $out/path
        HOME=$TMPDIR nix flake update --flake $out \
          --store ./. \
          --extra-experimental-features 'nix-command flakes'
      '';
in
pythonRuntime.pkgs.buildPythonApplication {
  name = "clan-cli";
  src = source;
  format = "pyproject";

  # Arguments for the wrapper to unset LD_LIBRARY_PATH to avoid glibc version issues
  makeWrapperArgs = [
    "--unset LD_LIBRARY_PATH"
    "--unset PYTHONPATH"

    # include selected runtime dependencies in the PATH
    "--prefix"
    "PATH"
    ":"
    (lib.makeBinPath (lib.attrValues bundledRuntimeDependenciesMap))

    # We need this for templates to work
    "--set"
    "CLAN_CORE_PATH"
    clan-core-path

    "--set"
    "CLAN_STATIC_PROGRAMS"
    (lib.concatStringsSep ":" (lib.attrNames bundledRuntimeDependenciesMap))
  ];

  nativeBuildInputs = [
    (pythonRuntime.withPackages (ps: [ ps.setuptools ]))
    installShellFiles
  ];

  propagatedBuildInputs = [ pythonRuntimeWithDeps ] ++ bundledRuntimeDependencies;

  # Define and expose the tests and checks to run in CI
  passthru.tests =
    (lib.mapAttrs' (n: lib.nameValuePair "clan-dep-${n}") testRuntimeDependenciesMap)
    // {
      clan-pytest-without-core =
        runCommand "clan-pytest-without-core" { nativeBuildInputs = testDependencies; }
          ''
            set -u -o pipefail
            cp -r ${source} ./src
            chmod +w -R ./src
            cd ./src

            export NIX_STATE_DIR=$TMPDIR/nix IN_NIX_SANDBOX=1 PYTHONWARNINGS=error

            # required to prevent concurrent 'nix flake lock' operations
            export CLAN_TEST_STORE=$TMPDIR/store
            export LOCK_NIX=$TMPDIR/nix_lock
            mkdir -p "$CLAN_TEST_STORE/nix/store"

            python -m pytest -m "not impure and not with_core" ./tests
            touch $out
          '';
      clan-pytest-with-core =
        runCommand "clan-pytest-with-core"
          {
            nativeBuildInputs = testDependencies;
            buildInputs = [
              pkgs.bash
              pkgs.coreutils
              pkgs.nix
            ];
            closureInfo = pkgs.closureInfo {
              rootPaths = [
                pkgs.bash
                pkgs.coreutils
                pkgs.jq.dev
                pkgs.stdenv
                pkgs.stdenvNoCC
              ];
            };
          }
          ''
            set -u -o pipefail
            cp -r ${source} ./src
            chmod +w -R ./src
            cd ./src

            export CLAN_CORE=${clan-core-path}
            export NIX_STATE_DIR=$TMPDIR/nix
            export IN_NIX_SANDBOX=1
            export PYTHONWARNINGS=error
            export CLAN_TEST_STORE=$TMPDIR/store
            # required to prevent concurrent 'nix flake lock' operations
            export LOCK_NIX=$TMPDIR/nix_lock
            mkdir -p "$CLAN_TEST_STORE/nix/store"
            xargs cp --recursive --target "$CLAN_TEST_STORE/nix/store"  < "$closureInfo/store-paths"
            nix-store --load-db --store "$CLAN_TEST_STORE" < "$closureInfo/registration"
            python -m pytest -m "not impure and with_core" ./tests
            touch $out
          '';
    };

  passthru.nixpkgs = nixpkgs';
  passthru.devshellPyDeps = ps: (pyTestDeps ps) ++ (pyDeps ps) ++ (devDeps ps);
  passthru.pythonRuntime = pythonRuntime;
  passthru.runtimeDependencies = bundledRuntimeDependencies;
  passthru.runtimeDependenciesMap = bundledRuntimeDependenciesMap;
  passthru.testRuntimeDependencies = testRuntimeDependencies;
  passthru.testRuntimeDependenciesMap = testRuntimeDependenciesMap;

  postInstall = ''
    cp -r ${nixpkgs'} $out/${pythonRuntime.sitePackages}/clan_cli/nixpkgs
    installShellCompletion --bash --name clan \
      <(${pythonRuntimeWithDeps.pkgs.argcomplete}/bin/register-python-argcomplete --shell bash clan)
    installShellCompletion --fish --name clan.fish \
      <(${pythonRuntimeWithDeps.pkgs.argcomplete}/bin/register-python-argcomplete --shell fish clan)
    installShellCompletion --zsh --name _clan \
      <(${pythonRuntimeWithDeps.pkgs.argcomplete}/bin/register-python-argcomplete --shell zsh clan)
  '';

  # Clean up after the package to avoid leaking python packages into a devshell
  # TODO: factor separate cli / API packages
  postFixup = ''
    rm $out/nix-support/propagated-build-inputs
  '';

  checkPhase = ''
    $out/bin/clan --help
  '';

  meta.mainProgram = "clan";
}
