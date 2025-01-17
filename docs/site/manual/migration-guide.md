# Migrate existing NixOS configurations

This guide will help you migrate your existing Nix configurations into Clan. Keep
in mind, though, this approach can be trickier and might lead to bugs or
unexpected issues. We recommend following the Getting Started guide first. Once
you have a working setup, you can easily transfer your Nix configurations over.

!!! Danger
    **Back up your existing configuration!**
    Before you start, it is strongly recommended to back up your existing
    configuration in any form you see fit. If you use version control to manage
    your configuration changes, it is also a good idea to follow the migration
    guide in a separte branch until everything works as expected.


## Starting Point

We assume you are already using NixOS flakes to manage your configuration. If
not, migrate to a flake-based setup following the official [NixOS
documentation](https://nix.dev/manual/nix/2.25/command-ref/new-cli/nix3-flake.html).
The snippet below shows a common Nix flake. For this example we will assume you
have have two hosts: **berlin** and **cologne**.

```nix
{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, ... }: {

    nixosConfigurations = {

      berlin = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [./machines/berlin/configuration.nix];
      };

      cologne = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [./machines/cologne/configuration.nix];
      };
    };
  };
}
```

## Add clan-core Input

Add `clan-core` to your flake as input. It will provide everything we need to
manage your configurations with clan.

```nix
inputs.clan-core = {
  url = "git+https://git.clan.lol/clan/clan-core";
  # Don't do this if your machines are on nixpkgs stable.
  inputs.nixpkgs.follows = "nixpkgs";
};
```

## Update Outputs

To be able to access our newly added dependency, it has to be added to the
output parameters.

```diff
-  outputs = { self, nixpkgs, ... }:
+  outputs = { self, nixpkgs, clan-core }:
```

The existing `nixosConfigurations` output of your flake will be created by
clan. In addition, a new `clanInternals` output will be added. Since both of
these are provided by the output of `lib.buildClan`, a common syntax is to use a
`let...in` statement to create your clan and access it's parameters in the flake
outputs.

For the provide flake example, your flake should now look like this:

```nix
{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, ... }:
  let
    clan = clan-core.lib.buildClan {
        directory = self; # this needs to point at the repository root
        specialArgs = {};
        inventory.meta.name = "NEEDS_TO_BE_UNIQUE"; # TODO: Changeme

        machines = {
            berlin = {
                nixpkgs.hostPlatform = "x86_64-linux";
                imports = [ ./machines/berlin/configuration.nix ];
            };
            cologne = {
                nixpkgs.hostPlatform = "x86_64-linux";
                imports = [ ./machines/cologne/configuration.nix ];
            };
        };
    };
  in
  {
      nixosConfigurations = clan.nixosConfigurations;
      inherit (clan) clanInternals;
  };
}
```

Et voilà! Your existing hosts are now part of a clan. Existing Nix tooling
should still work as normal. To check that you didn't make any errors, run `nix
flake show` and verify both hosts are still recognized as if nothing had
changed. You should also see the new `clanInternals` output.

```
❯ nix flake show
git+file:///my-nixos-config
├───clanInternals: unknown
└───nixosConfigurations
    ├───berlin: NixOS configuration
    └───cologne: NixOS configuration
```

Of course you can also rebuild your configuration using `nixos-rebuild` and
veryify everything still works.

## Add Clan CLI devShell

At this point Clan is set up, but you can't use the CLI yet. To do so, it is
recommended to expose it via a `devShell` in your flake. It is also possible to
install it any other way you would install a package in Nix, but using a
developtment shell ensures the CLI's version will always be in sync with your
configuration.

A minimal example is provided below, add it to your flake outputs.

```nix
devShells."x86_64-linux".default = nixpkgs.legacyPackages."x86_64-linux".mkShell {
  packages = [ clan-core.packages."x86_64-linux".clan-cli ];
};
```

To use the CLI, execute `nix develop` in the directory of your flake. The
resulting shell, provides you with the `clan` CLI tool. Since you will be using
it every time you interact with Clan, it is recommended to set up
[direnv](https://direnv.net/).

Verify everything works as expected by running `clan machines list`.

```
❯ nix develop
[user@host:~/my-nixos-config]$ clan machines list
berlin
cologne
```

## Specify Targets

Clan needs to know where it can reach your hosts. For each of your hosts, set
`clan.core.networking.targetHost` to its adress or hostname.

```nix
# machines/berlin/configuration.nix
{
  clan.core.networking.targetHost = "123.4.56.78";
}
```

## Next Steps

You are now fully set up. Use the CLI to manage your hosts or proceed to
configure further services. At this point you should be able to run commands
like `clan machines update berlin` to deploy a host.

