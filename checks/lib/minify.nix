{
  nixpkgs.flake.setFlakeRegistry = false;
  nixpkgs.flake.setNixPath = false;
  nix.registry.nixpkgs.to = { };
  documentation.doc.enable = false;
  documentation.man.enable = false;
}
