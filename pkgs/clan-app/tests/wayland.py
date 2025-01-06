import sys
from collections.abc import Generator
from subprocess import Popen
from typing import NewType

import pytest


@pytest.fixture(scope="session")
def wayland_compositor() -> Generator[Popen, None, None]:
    # Start the Wayland compositor (e.g., Weston)
    # compositor = Popen(["weston", "--backend=headless-backend.so"])
    compositor = Popen(["weston"])
    yield compositor
    # Cleanup: Terminate the compositor
    compositor.terminate()


GtkProc = NewType("GtkProc", Popen)


@pytest.fixture
def app() -> Generator[GtkProc, None, None]:
    cmd = [sys.executable, "-m", "clan_app"]
    print(f"Running: {cmd}")
    rapp = Popen(
        cmd, text=True, stdout=sys.stdout, stderr=sys.stderr, start_new_session=True
    )
    yield GtkProc(rapp)
    # Cleanup: Terminate your application
    rapp.terminate()
