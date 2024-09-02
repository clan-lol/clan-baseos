import json
from typing import TYPE_CHECKING

import pytest
from clan_cli.dirs import user_history_file
from clan_cli.history.add import HistoryEntry
from fixtures_flakes import FlakeForTest
from helpers import cli
from stdout import CaptureOutput

if TYPE_CHECKING:
    pass


@pytest.mark.impure
def test_history_add(
    test_flake_with_core: FlakeForTest,
) -> None:
    cmd = [
        "history",
        "add",
        f"clan://{test_flake_with_core.path}#vm1",
    ]
    cli.run(cmd)

    history_file = user_history_file()
    assert history_file.exists()
    history = [HistoryEntry(**entry) for entry in json.loads(history_file.read_text())]
    assert str(history[0].flake.flake_url) == str(test_flake_with_core.path)


@pytest.mark.impure
def test_history_list(
    capture_output: CaptureOutput,
    test_flake_with_core: FlakeForTest,
) -> None:
    with capture_output as output:
        cli.run(["history", "list"])
    assert str(test_flake_with_core.path) not in output.out

    cli.run(["history", "add", f"clan://{test_flake_with_core.path}#vm1"])

    with capture_output as output:
        cli.run(["history", "list"])
    assert str(test_flake_with_core.path) in output.out
