{
  inputs.clan-core.url = "https://git.clan.lol/clan/clan-core/archive/main.tar.gz";
  inputs.nixpkgs.follows = "clan-core/nixpkgs";

  outputs =
    { self, clan-core, ... }:
    let
      # Usage see: https://docs.clan.lol
      clan = clan-core.lib.buildClan { directory = self; };
    in
    {
      # all machines managed by Clan
      inherit (clan) nixosConfigurations clanInternals;
    };
}
