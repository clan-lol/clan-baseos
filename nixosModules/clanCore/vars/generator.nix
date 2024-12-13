{
  lib,
  config,
  pkgs,
  ...
}:
let
  inherit (lib)
    attrNames
    concatMapStrings
    genAttrs
    filterAttrs
    makeBinPath
    mkOptionDefault
    optionalString
    ;

  promptToFile = name: ''
    cat "$prompts/${name}" > "$out/${name}"
  '';

  promptsToFilesScript = concatMapStrings promptToFile;

  filePromptNames = attrNames (filterAttrs (_name: prompt: prompt.createFile) config.prompts);
in
{
  finalScript = mkOptionDefault (
    pkgs.writeScript "generator-${config.name}" ''
      set -eu -o pipefail

      export PATH="${makeBinPath config.runtimeInputs}:${pkgs.coreutils}/bin"

      ${optionalString (pkgs.stdenv.hostPlatform.isLinux) ''
        # prepare sandbox user on platforms where this is supported
        mkdir -p /etc

        cat > /etc/group <<EOF
        root:x:0:
        nixbld:!:$(id -g):
        nogroup:x:65534:
        EOF

        cat > /etc/passwd <<EOF
        root:x:0:0:Nix build user:/build:/noshell
        nixbld:x:$(id -u):$(id -g):Nix build user:/build:/noshell
        nobody:x:65534:65534:Nobody:/:/noshell
        EOF

        cat > /etc/hosts <<EOF
        127.0.0.1 localhost
        ::1 localhost
        EOF
      ''}
      ${promptsToFilesScript filePromptNames}
      ${config.script}
    ''
  );

  files = genAttrs filePromptNames (_name: { });
}
