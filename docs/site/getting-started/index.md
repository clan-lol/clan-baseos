# :material-clock-fast: Getting Started

Create your own clan with these initial steps and manage a fleet of machines with one single testable git repository!

### Prerequisites

=== "**Linux**"

    Clan depends on nix installed on your system. Run the following command to install nix.

    ```bash
    curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
    ```

    If you already have installed Nix, make sure you have the `nix-command` and `flakes` configuration enabled in your ~/.config/nix/nix.conf.
    The determinate installer already comes with this configuration by default.

    ```bash
    # /etc/nix/nix.conf or ~/.config/nix/nix.conf
    experimental-features = nix-command flakes
    ```

=== "**NixOS**"

    If you run NixOS the `nix` binary is already installed.

    You will also need to enable the `flakes` and `nix-commands` experimental features in your configuration.nix:

    ```nix
    { nix.settings.experimental-features = [ "nix-command" "flakes" ]; }
    ```

=== "**Other**"

    Clan doesn't offer dedicated support for other operating systems yet.

### Step 1: Add Clan CLI to Your Shell

Add the Clan CLI into your development workflow:

```bash
nix shell git+https://git.clan.lol/clan/clan-core#clan-cli
```

You can find reference documentation for the `clan` cli program [here](../reference/cli/index.md).

Alternatively you can check out the help pages directly:
```terminalSession
clan --help
```

### Step 2: Initialize Your Project

Set the foundation of your Clan project by initializing it as follows:

```bash
clan flakes create my-clan
```

This command creates the `flake.nix` and `.clan-flake` files for your project.
It will also generate files from a default template, to help show general clan usage patterns.

### Step 3: Verify the Project Structure

Ensure that all project files exist by running:

```bash
cd my-clan
tree
```

This should yield the following:

``` { .console .no-copy }
.
├── flake.nix
├── machines
│   ├── jon
│   │   ├── configuration.nix
│   │   └── hardware-configuration.nix
│   └── sara
│       ├── configuration.nix
│       └── hardware-configuration.nix
└── modules
    └── shared.nix

5 directories, 9 files
```

```bash
clan machines list
```

``` { .console .no-copy }
jon
sara
```

!!! success

    You just successfully bootstrapped your first clan directory.

---

### What's Next?

- [**Installer**](./installer.md): Setting up new computers remotely is easy with an USB stick.

---
