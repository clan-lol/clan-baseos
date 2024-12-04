import pytest
from fixtures_flakes import FlakeForTest
from helpers import cli
from stdout import CaptureOutput


@pytest.mark.impure
def test_machine_subcommands(
    test_flake_with_core: FlakeForTest,
    capture_output: CaptureOutput,
) -> None:
    cli.run(
        [
            "machines",
            "create",
            "--flake",
            str(test_flake_with_core.path),
            "machine1",
            "--tags",
            "vm",
        ]
    )

    with capture_output as output:
        cli.run(["machines", "list", "--flake", str(test_flake_with_core.path)])

    print(output.out)
    assert "machine1" in output.out
    assert "vm1" in output.out
    assert "vm2" in output.out

    cli.run(
        ["machines", "delete", "--flake", str(test_flake_with_core.path), "machine1"]
    )

    with capture_output as output:
        cli.run(["machines", "list", "--flake", str(test_flake_with_core.path)])
    assert "machine1" not in output.out
    assert "vm1" in output.out
    assert "vm2" in output.out
