from pathlib import Path

from clan_cli.clan_uri import ClanURI


def test_get_url() -> None:
    # Create a ClanURI object from a remote URI with parameters
    uri = ClanURI.from_str("clan://https://example.com?password=1234#myVM")
    assert uri.get_url() == "https://example.com?password=1234"

    uri = ClanURI.from_str("clan://~/Downloads")
    assert uri.get_url().endswith("/Downloads")

    uri = ClanURI.from_str("clan:///home/user/Downloads")
    assert uri.get_url() == "/home/user/Downloads"

    uri = ClanURI.from_str("clan://file:///home/user/Downloads")
    assert uri.get_url() == "/home/user/Downloads"


def test_local_uri() -> None:
    # Create a ClanURI object from a local URI
    uri = ClanURI.from_str("clan://file:///home/user/Downloads")
    assert uri.flake.path == Path("/home/user/Downloads")


def test_is_remote() -> None:
    # Create a ClanURI object from a remote URI
    uri = ClanURI.from_str("clan://https://example.com")
    assert uri.flake.url == "https://example.com"


def test_direct_local_path() -> None:
    # Create a ClanURI object from a remote URI
    uri = ClanURI.from_str("clan://~/Downloads")
    assert uri.get_url().endswith("/Downloads")


def test_direct_local_path2() -> None:
    # Create a ClanURI object from a remote URI
    uri = ClanURI.from_str("clan:///home/user/Downloads")
    assert uri.get_url() == "/home/user/Downloads"


def test_remote_with_clanparams() -> None:
    # Create a ClanURI object from a remote URI with parameters
    uri = ClanURI.from_str("clan://https://example.com")

    assert uri.machine_name == "defaultVM"
    assert uri.flake.url == "https://example.com"


def test_from_str_remote() -> None:
    uri = ClanURI.from_str(url="https://example.com", machine_name="myVM")
    assert uri.get_url() == "https://example.com"
    assert uri.machine_name == "myVM"
    assert uri.flake.url == "https://example.com"


def test_from_str_local() -> None:
    uri = ClanURI.from_str(url="~/Projects/democlan", machine_name="myVM")
    assert uri.get_url().endswith("/Projects/democlan")
    assert uri.machine_name == "myVM"
    assert uri.flake.is_local()
    assert str(uri.flake).endswith("/Projects/democlan")  # type: ignore


def test_from_str_local_no_machine() -> None:
    uri = ClanURI.from_str("~/Projects/democlan")
    assert uri.get_url().endswith("/Projects/democlan")
    assert uri.machine_name == "defaultVM"
    assert uri.flake.is_local()
    assert str(uri.flake).endswith("/Projects/democlan")  # type: ignore


def test_from_str_local_no_machine2() -> None:
    uri = ClanURI.from_str("~/Projects/democlan#syncthing-peer1")
    assert uri.get_url().endswith("/Projects/democlan")
    assert uri.machine_name == "syncthing-peer1"
    assert uri.flake.is_local()
    assert str(uri.flake).endswith("/Projects/democlan")  # type: ignore
