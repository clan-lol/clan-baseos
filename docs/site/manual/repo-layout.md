
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

