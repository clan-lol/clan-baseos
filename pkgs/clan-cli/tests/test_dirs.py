# from clan_cli.dirs import _get_clan_flake_toplevel

# TODO: Reimplement test?
# def test_get_clan_flake_toplevel(
#     monkeypatch: pytest.MonkeyPatch, temporary_home: Path
# ) -> None:
#     monkeypatch.chdir(temporary_home)
#     with pytest.raises(ClanError):
#         print(_get_clan_flake_toplevel())
#     (temporary_home / ".git").touch()
#     assert _get_clan_flake_toplevel() == temporary_home

#     subdir = temporary_home / "subdir"
#     subdir.mkdir()
#     monkeypatch.chdir(subdir)
#     (subdir / ".clan-flake").touch()
#     assert _get_clan_flake_toplevel() == subdir

from clan_cli.dirs import clan_key_safe, vm_state_dir


def test_clan_key_safe() -> None:
    assert clan_key_safe("/foo/bar") == "%2Ffoo%2Fbar"


def test_vm_state_dir_identity() -> None:
    dir1 = vm_state_dir("https://some.clan", "vm1")
    dir2 = vm_state_dir("https://some.clan", "vm1")
    assert str(dir1) == str(dir2)


def test_vm_state_dir_no_collision() -> None:
    dir1 = vm_state_dir("/foo/bar", "vm1")
    dir2 = vm_state_dir("https://some.clan", "vm1")
    assert str(dir1) != str(dir2)
