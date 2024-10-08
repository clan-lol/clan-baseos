{
  lib,
  writers,
  writeShellScriptBin,
  localsend,
  alias ? null,
}:
let
  localsend-ensure-config = writers.writePython3 "localsend-ensure-config" {
    flakeIgnore = [
      # We don't live in the dark ages anymore.
      # Languages like Python that are whitespace heavy will overrun
      # 79 characters..
      "E501"
    ];
  } (builtins.readFile ./localsend-ensure-config.py);
in
writeShellScriptBin "localsend" ''
  set -xeu
  ${localsend-ensure-config} ${lib.optionalString (alias != null) alias}
  ${lib.getExe localsend}
''
