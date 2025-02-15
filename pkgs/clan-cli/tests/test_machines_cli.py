import pytest
from clan_cli.inventory import load_inventory_json
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

    inventory: dict = dict(load_inventory_json(str(test_flake_with_core.path)))
    assert "machine1" in inventory["machines"]
    assert "service" not in inventory

    with capture_output as output:
        cli.run(["machines", "list", "--flake", str(test_flake_with_core.path)])

    print(output.out)
    assert "machine1" in output.out
    assert "vm1" in output.out
    assert "vm2" in output.out

    cli.run(
        ["machines", "delete", "--flake", str(test_flake_with_core.path), "machine1"]
    )

    inventory_2: dict = dict(load_inventory_json(str(test_flake_with_core.path)))
    assert "machine1" not in inventory_2["machines"]
    assert "service" not in inventory_2

    with capture_output as output:
        cli.run(["machines", "list", "--flake", str(test_flake_with_core.path)])
    assert "machine1" not in output.out
    assert "vm1" in output.out
    assert "vm2" in output.out
