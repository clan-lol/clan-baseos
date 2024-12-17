{
  lib,
  nix-unit,
  clan-cli,
  clan-cli-full,
  mkShell,
  ruff,
  python3,
  self',
}:
let
  devshellTestDeps =
    clan-cli.passthru.testDependencies
    ++ (with python3.pkgs; [
      rope
      setuptools
      wheel
      webcolors
      pip
    ]);
in
mkShell {
  buildInputs = [
    nix-unit
    ruff
  ] ++ devshellTestDeps;

  inputsFrom = [ self'.devShells.default ];

  CLAN_STATIC_PROGRAMS = lib.concatStringsSep ":" (
    lib.attrNames clan-cli-full.passthru.runtimeDependenciesMap
  );

  shellHook = ''
    export GIT_ROOT="$(git rev-parse --show-toplevel)"
    export PKG_ROOT="$GIT_ROOT/pkgs/clan-cli"
    export PYTHONWARNINGS=error

    # Add current package to PYTHONPATH
    export PYTHONPATH="$PKG_ROOT''${PYTHONPATH:+:$PYTHONPATH:}"

    # Add clan command to PATH
    export PATH="$PKG_ROOT/bin":"$PATH"

    # Needed for impure tests
    ln -sfT ${clan-cli.nixpkgs} "$PKG_ROOT/clan_cli/nixpkgs"

    # Generate classes.py from inventory schema
    # This file is in .gitignore
    ${self'.packages.classgen}/bin/classgen ${self'.legacyPackages.schemas.inventory-schema-abstract}/schema.json $PKG_ROOT/clan_cli/inventory/classes.py --stop-at "Service"
  '';
}
