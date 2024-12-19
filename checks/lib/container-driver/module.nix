{
  hostPkgs,
  lib,
  config,
  ...
}:
let
  testDriver = hostPkgs.python3.pkgs.callPackage ./package.nix {
    inherit (config) extraPythonPackages;
    inherit (hostPkgs.pkgs) util-linux systemd nix;
  };
  containers =
    testScript:
    map (m: [
      m.system.build.toplevel
      (hostPkgs.closureInfo {
        rootPaths = [
          m.system.build.toplevel
          (hostPkgs.writeText "testScript" testScript)
        ];
      })
    ]) (lib.attrValues config.nodes);
  pythonizeName =
    name:
    let
      head = lib.substring 0 1 name;
      tail = lib.substring 1 (-1) name;
    in
    (if builtins.match "[A-z_]" head == null then "_" else head)
    + lib.stringAsChars (c: if builtins.match "[A-z0-9_]" c == null then "_" else c) tail;
  nodeHostNames =
    let
      nodesList = map (c: c.system.name) (lib.attrValues config.nodes);
    in
    nodesList ++ lib.optional (lib.length nodesList == 1 && !lib.elem "machine" nodesList) "machine";
  machineNames = map (name: "${name}: Machine;") pythonizedNames;
  pythonizedNames = map pythonizeName nodeHostNames;
in
{
  driver = lib.mkForce (
    hostPkgs.runCommand "nixos-test-driver-${config.name}"
      {
        nativeBuildInputs = [
          hostPkgs.makeWrapper
        ] ++ lib.optionals (!config.skipTypeCheck) [ hostPkgs.mypy ];
        buildInputs = [ testDriver ];
        testScript = config.testScriptString;
        preferLocalBuild = true;
        passthru = config.passthru;
        meta = config.meta // {
          mainProgram = "nixos-test-driver";
        };
      }
      ''
        mkdir -p $out/bin

        ${lib.optionalString (!config.skipTypeCheck) ''
          # prepend type hints so the test script can be type checked with mypy
          cat "${./test-script-prepend.py}" >> testScriptWithTypes
          echo "${builtins.toString machineNames}" >> testScriptWithTypes
          echo -n "$testScript" >> testScriptWithTypes

          echo "Running type check (enable/disable: config.skipTypeCheck)"
          echo "See https://nixos.org/manual/nixos/stable/#test-opt-skipTypeCheck"

          mypy  --no-implicit-optional \
                --pretty \
                --no-color-output \
                testScriptWithTypes
        ''}

        echo -n "$testScript" >> $out/test-script

        ln -s ${testDriver}/bin/nixos-test-driver $out/bin/nixos-test-driver

        wrapProgram $out/bin/nixos-test-driver \
          ${
            lib.concatStringsSep " " (
              map (container: "--add-flags '--container ${builtins.toString container}'") (
                containers config.testScriptString
              )
            )
          } \
          --add-flags "--test-script '$out/test-script'"
      ''
  );

  test = lib.mkForce (
    lib.lazyDerivation {
      # lazyDerivation improves performance when only passthru items and/or meta are used.
      derivation = hostPkgs.stdenv.mkDerivation {
        name = "vm-test-run-${config.name}";

        requiredSystemFeatures = [ "uid-range" ];

        buildCommand = ''
          mkdir -p $out

          # effectively mute the XMLLogger
          export LOGFILE=/dev/null

          ${config.driver}/bin/nixos-test-driver -o $out
        '';

        passthru = config.passthru;

        meta = config.meta;
      };
      inherit (config) passthru meta;
    }
  );
}
