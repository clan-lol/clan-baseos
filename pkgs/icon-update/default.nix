{ pkgs, deno }:
let
  src = ./.;
in
pkgs.writeShellApplication {
  name = "update";

  runtimeInputs = [ deno ];
  runtimeEnv = {
    FIGMA_ICON_FILE_ID = "KJgLnsBI9nvUt44qKJXmVm";
    FRAME_ID = "709-324";
  };

  text = ''
    OUT_DIR=$(realpath ../webview-ui/app/icons)
    deno run --allow-all ${src}/main.ts
  '';
}
