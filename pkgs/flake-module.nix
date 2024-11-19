{ inputs, ... }:

{
  imports = [
    ./clan-cli/flake-module.nix
    ./clan-app/flake-module.nix
    ./clan-vm-manager/flake-module.nix
    ./installer/flake-module.nix
    ./webview-ui/flake-module.nix
    ./distro-packages/flake-module.nix
    ./icon-update/flake-module.nix
  ];

  flake.packages.x86_64-linux =
    let
      pkgs = inputs.nixpkgs.legacyPackages.x86_64-linux;
    in
    {
      yagna = pkgs.callPackage ./yagna { };
    };

  perSystem =
    { config, pkgs, ... }:
    {
      packages = {
        tea-create-pr = pkgs.callPackage ./tea-create-pr { formatter = config.treefmt.build.wrapper; };
        zerotier-members = pkgs.callPackage ./zerotier-members { };
        zt-tcp-relay = pkgs.callPackage ./zt-tcp-relay { };
        moonlight-sunshine-accept = pkgs.callPackage ./moonlight-sunshine-accept { };
        merge-after-ci = pkgs.callPackage ./merge-after-ci { inherit (config.packages) tea-create-pr; };
        pending-reviews = pkgs.callPackage ./pending-reviews { };
        editor = pkgs.callPackage ./editor/clan-edit-codium.nix { };
        classgen = pkgs.callPackage ./classgen { };
        zerotierone = pkgs.callPackage ./zerotierone { };
      };
    };
}
