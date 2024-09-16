{
  outputs =
    { ... }:
    {
      templates = {
        default = {
          description = "Initialize a new clan flake";
          path = ./new-clan;
        };
        minimal = {
          description = "for clans managed via (G)UI";
          path = ./minimal;
        };
        flake-parts = {
          description = "Flake-parts";
          path = ./flake-parts;
        };
        flash-installer = {
          description = "Flash installer";
          path = ./flash-installer;
        };
      };
    };
}
