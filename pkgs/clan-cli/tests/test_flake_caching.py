import pytest
from clan_cli.flake import Flake, FlakeCacheEntry
from fixtures_flakes import ClanFlake


def test_select() -> None:
    testdict = {"x": {"y": [123, 345, 456], "z": "bla"}}
    test_cache = FlakeCacheEntry(testdict, [])
    assert test_cache["x"]["z"].value == "bla"
    assert test_cache.is_cached(["x", "z"])
    assert test_cache.select(["x", "y", 0]) == 123
    assert not test_cache.is_cached(["x", "z", 1])


def test_out_path() -> None:
    testdict = {"x": {"y": [123, 345, 456], "z": "/nix/store/bla"}}
    test_cache = FlakeCacheEntry(testdict, [])
    assert test_cache.select(["x", "z"]) == "/nix/store/bla"
    assert test_cache.select(["x", "z", "outPath"]) == "/nix/store/bla"


@pytest.mark.with_core
def test_flake_caching(flake: ClanFlake) -> None:
    m1 = flake.machines["machine1"]
    m1["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    flake.machines["machine2"] = m1.copy()
    flake.machines["machine3"] = m1.copy()
    flake.refresh()

    flake_ = Flake(str(flake.path))
    hostnames = flake_.select("nixosConfigurations.*.config.networking.hostName")
    assert hostnames == {
        "machine1": "machine1",
        "machine2": "machine2",
        "machine3": "machine3",
    }
