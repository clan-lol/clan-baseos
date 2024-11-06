{ pkgs }:
pkgs.mkShell {
  packages = with pkgs; [ deno ];
  env = {
    FIGMA_ICON_FILE_ID = "KJgLnsBI9nvUt44qKJXmVm";
    FRAME_ID = "709-324";
    OUT_DIR = "./icons";
  };
}
