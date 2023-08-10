{ age
, argcomplete
, black
, bubblewrap
, installShellFiles
, jsonschema
, mypy
, nix
, openssh
, pytest
, pytest-cov
, pytest-subprocess
, python3
, ruff
, runCommand
, self
, setuptools
, sops
, stdenv
, wheel
, zerotierone
}:
let
  dependencies = [ argcomplete jsonschema ];

  testDependencies = [
    pytest
    pytest-cov
    pytest-subprocess
    mypy
    openssh
    stdenv.cc
  ];

  checkPython = python3.withPackages (_ps: dependencies ++ testDependencies);

  # - vendor the jsonschema nix lib (copy instead of symlink).
  # - lib.cleanSource prevents unnecessary rebuilds when `self` changes.
  source = runCommand "clan-cli-source" { } ''
    cp -r ${./.} $out
    chmod -R +w $out
    rm $out/clan_cli/config/jsonschema
    cp -r ${self + /lib/jsonschema} $out/clan_cli/config/jsonschema
  '';
in
python3.pkgs.buildPythonPackage {
  name = "clan-cli";
  src = source;
  format = "pyproject";
  nativeBuildInputs = [
    setuptools
    installShellFiles
  ];
  propagatedBuildInputs = dependencies;

  passthru.tests = {
    clan-mypy = runCommand "clan-mypy" { } ''
      cp -r ${source} ./src
      chmod +w -R ./src
      cd ./src
      ${checkPython}/bin/mypy .
      touch $out
    '';
    clan-pytest = runCommand "clan-tests"
      {
        nativeBuildInputs = [ age zerotierone bubblewrap sops nix openssh stdenv.cc ];
      } ''
      cp -r ${source} ./src
      chmod +w -R ./src
      cd ./src
      ${checkPython}/bin/python -m pytest ./tests
      touch $out
    '';
  };

  passthru.devDependencies = [
    ruff
    black
    setuptools
    wheel
  ] ++ testDependencies;

  makeWrapperArgs = [
    "--set CLAN_FLAKE ${self}"
  ];

  postInstall = ''
    installShellCompletion --bash --name clan \
      <(${argcomplete}/bin/register-python-argcomplete --shell bash clan)
    installShellCompletion --fish --name clan.fish \
      <(${argcomplete}/bin/register-python-argcomplete --shell fish clan)
  '';
  checkPhase = ''
    PYTHONPATH= $out/bin/clan --help
    if grep --include \*.py -Rq "breakpoint()" $out; then
      echo "breakpoint() found in $out:"
      grep --include \*.py -Rn "breakpoint()" $out
      exit 1
    fi
  '';
  meta.mainProgram = "clan";
}
