import logging
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

log = logging.getLogger(__name__)


@pytest.fixture
def temporary_home(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="pytest-home-") as dirpath:
        xdg_runtime_dir = os.getenv("XDG_RUNTIME_DIR")
        monkeypatch.setenv("HOME", str(dirpath))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(Path(dirpath) / ".config"))

        runtime_dir = Path(dirpath) / "xdg-runtime-dir"
        runtime_dir.mkdir()
        runtime_dir.chmod(0o700)

        gpgdir = runtime_dir / "gpgagent"
        gpgdir.mkdir()
        gpgdir.chmod(0o700)
        monkeypatch.setenv("GPG_AGENT_INFO", str(gpgdir))

        # Iterate over all environment variables
        for key, value in os.environ.items():
            if xdg_runtime_dir and value.startswith(xdg_runtime_dir):
                monkeypatch.setenv(
                    key, value.replace(xdg_runtime_dir, str(runtime_dir))
                )

        monkeypatch.setenv("XDG_RUNTIME_DIR", str(runtime_dir))
        monkeypatch.chdir(str(dirpath))
        yield Path(dirpath)


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="pytest-") as dirpath:
        yield Path(dirpath)
