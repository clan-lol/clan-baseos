{ ... }:
{
  disko = {
    single-disk = {
      description = "A simple ext4 disk with a single partition";
      path = ./disk/single-disk;
    };
  };

  machine = {
    flash-installer = {
      description = "Initialize a new flash-installer machine";
      path = ./clan/machineTemplates/machines/flash-installer;
    };
    new-machine = {
      description = "Initialize a new machine";
      path = ./clan/machineTemplates/machines/new-machine;
    };
  };

  clan = {
    default = {
      description = "Initialize a new clan flake";
      path = ./clan/new-clan;
    };
    minimal = {
      description = "for clans managed via (G)UI";
      path = ./clan/minimal;
    };
    flake-parts = {
      description = "Flake-parts";
      path = ./clan/flake-parts;
    };
    minimal-flake-parts = {
      description = "Minimal flake-parts clan template";
      path = ./clan/minimal-flake-parts;
    };
  };
}
