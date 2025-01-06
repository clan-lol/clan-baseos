from wayland import GtkProc


def test_open(app: GtkProc) -> None:
    assert app.poll() is None
