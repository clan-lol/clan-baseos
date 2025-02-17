import json
import subprocess
from pathlib import Path

import pytest
from clan_cli.cmd import run
from fixtures_flakes import substitute
from helpers import cli
from stdout import CaptureOutput


@pytest.mark.impure
def test_create_flake(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    clan_core: Path,
    capture_output: CaptureOutput,
) -> None:
    flake_dir = temporary_home / "test-flake"

    cli.run(["flakes", "create", str(flake_dir), "--template=default"])

    assert (flake_dir / ".clan-flake").exists()
    # Replace the inputs.clan.url in the template flake.nix
    substitute(
        flake_dir / "flake.nix",
        clan_core,
    )
    # Dont evaluate the inventory before the substitute call

    monkeypatch.chdir(flake_dir)
    cli.run(["machines", "create", "machine1"])

    # create a hardware-configuration.nix that doesn't throw an eval error

    for patch_machine in ["jon", "sara"]:
        (
            flake_dir / "machines" / f"{patch_machine}/hardware-configuration.nix"
        ).write_text("{}")

    with capture_output as output:
        cli.run(["machines", "list"])
    assert "machine1" in output.out
    flake_show = subprocess.run(
        ["nix", "flake", "show", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    flake_outputs = json.loads(flake_show.stdout)
    try:
        flake_outputs["nixosConfigurations"]["machine1"]
    except KeyError:
        pytest.fail("nixosConfigurations.machine1 not found in flake outputs")


@pytest.mark.impure
def test_create_flake_existing_git(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    clan_core: Path,
    capture_output: CaptureOutput,
) -> None:
    flake_dir = temporary_home / "test-flake"

    run(["git", "init", str(temporary_home)])

    cli.run(["flakes", "create", str(flake_dir), "--template=default"])

    assert (flake_dir / ".clan-flake").exists()
    # Replace the inputs.clan.url in the template flake.nix
    substitute(
        flake_dir / "flake.nix",
        clan_core,
    )
    # Dont evaluate the inventory before the substitute call

    monkeypatch.chdir(flake_dir)
    cli.run(["machines", "create", "machine1"])

    # create a hardware-configuration.nix that doesn't throw an eval error

    for patch_machine in ["jon", "sara"]:
        (
            flake_dir / "machines" / f"{patch_machine}/hardware-configuration.nix"
        ).write_text("{}")

    with capture_output as output:
        cli.run(["machines", "list"])
    assert "machine1" in output.out
    flake_show = subprocess.run(
        ["nix", "flake", "show", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    flake_outputs = json.loads(flake_show.stdout)
    try:
        flake_outputs["nixosConfigurations"]["machine1"]
    except KeyError:
        pytest.fail("nixosConfigurations.machine1 not found in flake outputs")


@pytest.mark.impure
def test_ui_template(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    clan_core: Path,
    capture_output: CaptureOutput,
) -> None:
    flake_dir = temporary_home / "test-flake"
    cli.run(["flakes", "create", str(flake_dir), "--template=minimal"])

    # Replace the inputs.clan.url in the template flake.nix
    substitute(
        flake_dir / "flake.nix",
        clan_core,
    )

    monkeypatch.chdir(flake_dir)
    cli.run(["machines", "create", "machine1"])

    with capture_output as output:
        cli.run(["machines", "list"])
    assert "machine1" in output.out
    flake_show = subprocess.run(
        ["nix", "flake", "show", "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    flake_outputs = json.loads(flake_show.stdout)
    try:
        flake_outputs["nixosConfigurations"]["machine1"]
    except KeyError:
        pytest.fail("nixosConfigurations.machine1 not found in flake outputs")
