{
  # this placeholder is replaced by the path to nixpkgs
  inputs.nixpkgs.url = "__NIXPKGS__";

  outputs =
    inputs':
    let
      # fake clan-core input
      fake-clan-core = {
        clanModules.fake-module = ./fake-module.nix;
      };
      inputs = inputs' // {
        clan-core = fake-clan-core;
      };
    in
    {
      nixosConfigurations.machine1 = inputs.nixpkgs.lib.nixosSystem {
        modules = [
          ./nixosModules/machine1.nix
          (
            {
              ...
            }:
            {
              config = {
                nixpkgs.hostPlatform = "x86_64-linux";
                # speed up by not instantiating nixpkgs twice and disable documentation
                nixpkgs.pkgs = inputs.nixpkgs.legacyPackages.x86_64-linux;
                documentation.enable = false;
              };
            }
          )
        ];
      };
    };
}
