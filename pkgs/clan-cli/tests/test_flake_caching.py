from clan_cli.flake import FlakeCacheEntry
from fixtures_flakes import ClanFlake


def test_flake_caching(test_flake: ClanFlake) -> None:
    testdict = {"x": {"y": [123, 345, 456], "z": "bla"}}
    test_cache = FlakeCacheEntry(testdict, [])
    assert test_cache["x"]["z"].value == "bla"
    assert test_cache.is_cached(["x", "z"])
    assert test_cache.select(["x", "y", 0]) == 123
    assert not test_cache.is_cached(["x", "z", 1])
    # TODO check this, but test_flake is not a  real clan flake (no clan-core, no clanInternals)
    # cmd.run(["nix", "flake", "lock"], cmd.RunOpts(cwd=test_flake.path))
    # flake = Flake(str(test_flake.path))
    # hostnames = flake.select("nixosConfigurations.*.config.networking.hostName")
