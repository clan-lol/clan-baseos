
Clan supports integration with [flake.parts](https://flake.parts/) a tool which allows composing nixos modules in a modular way.

Here's how to set up Clan using `nix flakes` and `flake-parts`.

## 1. Update Your Flake Inputs

To begin, you'll need to add `flake-parts` as a new dependency in your flake's inputs. This is alongside the already existing dependencies, such as `clan-core` and `nixpkgs`. Here's how you can update your `flake.nix` file:

```nix
# flake.nix
inputs = {
  nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";

  # New flake-parts input
  flake-parts.url = "github:hercules-ci/flake-parts";
  flake-parts.inputs.nixpkgs-lib.follows = "nixpkgs";

  clan-core = {
    url = "git+https://git.clan.lol/clan/clan-core";
    inputs.nixpkgs.follows = "nixpkgs"; # Needed if your configuration uses nixpkgs unstable.
    # New
    inputs.flake-parts.follows = "flake-parts";
  };
}
```

## 2. Import Clan-Core Flake Module

After updating your flake inputs, the next step is to import the `clan-core` flake module. This will make the [clan options](../reference/nix-api/buildclan.md) available within `mkFlake`.

```nix
  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } (
      {
        #
        imports = [
          inputs.clan-core.flakeModules.default
        ];
      }
    );
```

### 3. Configure Clan Settings and Define Machines

Configure your clan settings and define machine configurations.

Below is a guide on how to structure this in your flake.nix:

```nix
  outputs = inputs@{ flake-parts, clan-core, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } ({self, pkgs, ...}: {
      # We define our own systems below. you can still use this to add system specific outputs to your flake.
      # See: https://flake.parts/getting-started
      systems = [];

      # import clan-core modules
      imports = [
        clan-core.flakeModules.default
      ];
      # Define your clan
      # See: https://docs.clan.lol/reference/nix-api/buildclan/
      clan = {
        # Clan wide settings. (Required)
        meta.name = ""; # Ensure to choose a unique name.

        machines = {
          jon = {
            imports = [
              ./machines/jon/configuration.nix
              ./modules/disko.nix
              # ... more modules
            ];
            nixpkgs.hostPlatform = "x86_64-linux";

            # Set this for clan commands use ssh i.e. `clan machines update`
            clan.core.networking.targetHost = pkgs.lib.mkDefault "root@jon";

            # remote> lsblk --output NAME,ID-LINK,FSTYPE,SIZE,MOUNTPOINT
            disko.devices.disk.main = {
              device = "/dev/disk/by-id/nvme-eui.e8238fa6bf530001001b448b4aec2929";
            };

            # There needs to be exactly one controller per clan
            clan.core.networking.zerotier.controller.enable = true;

          };
        };
      };
    });
```

For detailed information about configuring `flake-parts` and the available options within Clan,
refer to the Clan module documentation located [here](https://git.clan.lol/clan/clan-core/src/branch/main/flakeModules/clan.nix).

---
