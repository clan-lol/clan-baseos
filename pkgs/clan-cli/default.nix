{
  # callPackage args
  argcomplete,
  gitMinimal,
  gnupg,
  installShellFiles,
  lib,
  nix,
  pkgs,
  pytest-cov,
  pytest-subprocess,
  pytest-timeout,
  pytest-xdist,
  pytest,
  python3,
  runCommand,
  setuptools,
  stdenv,

  # custom args
  clan-core-path,
  nixpkgs,
  includedRuntimeDeps,

  inventory-schema,
  classgen,
}:
let
  pythonDependencies = [
    argcomplete # Enables shell completions
  ];

  # load nixpkgs runtime dependencies from a json file
  # This file represents an allow list at the same time that is checked by the run_cmd
  #   implementation in nix.py
  runtimeDependenciesAsSet = lib.filterAttrs (_name: pkg: !pkg.meta.unsupported or false) (
    lib.genAttrs (lib.importJSON ./clan_cli/nix/allowed-programs.json) (name: pkgs.${name})
  );

  runtimeDependencies = lib.attrValues runtimeDependenciesAsSet;

  testDependencies =
    runtimeDependencies
    ++ [
      gnupg
      stdenv.cc # Compiler used for certain native extensions
    ]
    ++ pythonDependencies
    ++ [
      pytest
      pytest-cov # Generate coverage reports
      pytest-subprocess # fake the real subprocess behavior to make your tests more independent.
      pytest-xdist # Run tests in parallel on multiple cores
      pytest-timeout # Add timeouts to your tests
    ];

  # Setup Python environment with all dependencies for running tests
  pythonWithTestDeps = python3.withPackages (_ps: testDependencies);

  source = runCommand "clan-cli-source" { } ''
    cp -r ${./.} $out
    chmod -R +w $out
    ln -sf ${nixpkgs'} $out/clan_cli/nixpkgs
    cp -r ${../../templates} $out/clan_cli/templates

    ${classgen}/bin/classgen ${inventory-schema}/schema.json $out/clan_cli/inventory/classes.py --stop-at "Service"
  '';

  # Create a custom nixpkgs for use within the project
  nixpkgs' = runCommand "nixpkgs" { nativeBuildInputs = [ nix ]; } ''
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
    nix flake update $out \
      --store ./. \
      --extra-experimental-features 'nix-command flakes'
  '';
in
python3.pkgs.buildPythonApplication {
  name = "clan-cli";
  src = source;
  format = "pyproject";

  # Arguments for the wrapper to unset LD_LIBRARY_PATH to avoid glibc version issues
  makeWrapperArgs =
    [
      "--unset LD_LIBRARY_PATH"

      # TODO: remove gitMinimal here and use the one from runtimeDependencies
      "--suffix"
      "PATH"
      ":"
      "${gitMinimal}/bin/git"
    ]
    # include selected runtime dependencies in the PATH
    ++ lib.concatMap (p: [
      "--prefix"
      "PATH"
      ":"
      p
    ]) includedRuntimeDeps
    ++ [
      "--set"
      "CLAN_STATIC_PROGRAMS"
      (lib.concatStringsSep ":" includedRuntimeDeps)
    ];

  nativeBuildInputs = [
    setuptools
    installShellFiles
  ];

  propagatedBuildInputs = pythonDependencies;

  # Define and expose the tests and checks to run in CI
  passthru.tests =
    (lib.mapAttrs' (n: lib.nameValuePair "clan-dep-${n}") runtimeDependenciesAsSet)
    // {
      clan-pytest-without-core =
        runCommand "clan-pytest-without-core"
          { nativeBuildInputs = [ pythonWithTestDeps ] ++ testDependencies; }
          ''
            cp -r ${source} ./src
            chmod +w -R ./src
            cd ./src

            export NIX_STATE_DIR=$TMPDIR/nix IN_NIX_SANDBOX=1
            ${pythonWithTestDeps}/bin/python -m pytest -m "not impure and not with_core" ./tests
            touch $out
          '';
      clan-pytest-with-core =
        runCommand "clan-pytest-with-core"
          { nativeBuildInputs = [ pythonWithTestDeps ] ++ testDependencies; }
          ''
            cp -r ${source} ./src
            chmod +w -R ./src
            cd ./src

            export CLAN_CORE=${clan-core-path}
            export NIX_STATE_DIR=$TMPDIR/nix IN_NIX_SANDBOX=1
            ${pythonWithTestDeps}/bin/python -m pytest -m "not impure and with_core" ./tests
            touch $out
          '';
    };

  passthru.nixpkgs = nixpkgs';
  passthru.testDependencies = testDependencies;
  passthru.pythonWithTestDeps = pythonWithTestDeps;
  passthru.runtimeDependencies = runtimeDependencies;
  passthru.runtimeDependenciesAsSet = runtimeDependenciesAsSet;

  postInstall = ''
    cp -r ${nixpkgs'} $out/${python3.sitePackages}/clan_cli/nixpkgs
    installShellCompletion --bash --name clan \
      <(${argcomplete}/bin/register-python-argcomplete --shell bash clan)
    installShellCompletion --fish --name clan.fish \
      <(${argcomplete}/bin/register-python-argcomplete --shell fish clan)
    installShellCompletion --zsh --name _clan \
      <(${argcomplete}/bin/register-python-argcomplete --shell bash clan)
  '';

  # Clean up after the package to avoid leaking python packages into a devshell
  # TODO: factor seperate cli / API packages
  postFixup = ''
    rm $out/nix-support/propagated-build-inputs
  '';

  checkPhase = ''
    PYTHONPATH= $out/bin/clan --help
  '';

  meta.mainProgram = "clan";
}
