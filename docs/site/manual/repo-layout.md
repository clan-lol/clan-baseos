# Repo Layout Guide

This guide will help you navigate the codebase and locate key files:

```bash
$ tree -L 1
.
├── checks          # Contains NixOS and VM tests
├── clanModules     # Clan modules available for end-user import
├── docs            # Source files for docs.clan.lol, generated with MkDocs
├── flakeModules
├── lib             # User-exposed Clan Nix functions like buildClan and inventory
├── machines
├── nixosModules    # Internal Clan Nix functions, e.g., clanCore
├── pkgs            # Clan applications and packaged dependencies
├── formatter.nix   # Configuration for nix-treefmt, manages `nix fmt`
├── scripts
├── sops
├── templates       # Template files for creating a new Clan
└── vars
```

## Getting Started with Infrastructure

To dive into infrastructure, check out our clan infra repo: [clan-infra](https://git.clan.lol/clan/clan-infra). Please provide us with your public SOPS key so we can add you as an admin.

## Related Projects

- **Data Mesher**: [dm](https://git.clan.lol/clan/dm)
- **Nixos Facter**: [nixos-facter](https://github.com/nix-community/nixos-facter)
- **Nixos Anywhere**: [nixos-anywhere](https://github.com/nix-community/nixos-anywhere)
- **Disko**: [disko](https://github.com/nix-community/disko)

## Fixing Bugs or Adding Features in Clan-CLI

If you have a bug fix or feature that involves a related project, clone the relevant repository and replace its invocation in your local setup.

For instance, if you need to update `nixos-anywhere` in clan-cli, find its usage:

```python
run(
    nix_shell(
        ["nixpkgs#nixos-anywhere"],
        cmd,
    ),
    RunOpts(log=Log.BOTH, prefix=machine.name, needs_user_terminal=True),
)
```

You can replace `"nixpkgs#nixos-anywhere"` with your local path:

```python
run(
    nix_shell(
        ["<path_to_local_src>#nixos-anywhere"],
        cmd,
    ),
    RunOpts(log=Log.BOTH, prefix=machine.name, needs_user_terminal=True),
)
```
