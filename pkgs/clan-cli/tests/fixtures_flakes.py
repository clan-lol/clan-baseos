import json
import logging
import os
import shutil
import subprocess as sp
import tempfile
from collections import defaultdict
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

import pytest
from clan_cli.dirs import nixpkgs_source
from clan_cli.locked_open import locked_open
from fixture_error import FixtureError
from root import CLAN_CORE

log = logging.getLogger(__name__)

lock_nix = os.environ.get("LOCK_NIX", "")
if not lock_nix:
    lock_nix = tempfile.NamedTemporaryFile().name  # NOQA: SIM115


# allows defining nested dictionary in a single line
def def_value() -> defaultdict:
    return defaultdict(def_value)


nested_dict: Callable[[], dict[str, Any]] = lambda: defaultdict(def_value)


# Substitutes strings in a file.
# This can be used on the flake.nix or default.nix of a machine
def substitute(
    file: Path,
    clan_core_flake: Path | None = None,
    flake: Path = Path(__file__).parent,
) -> None:
    sops_key = str(flake.joinpath("sops.key"))
    buf = ""
    with file.open() as f:
        for line in f:
            line = line.replace("__NIXPKGS__", str(nixpkgs_source()))
            if clan_core_flake:
                line = line.replace("__CLAN_CORE__", str(clan_core_flake))
                line = line.replace(
                    "git+https://git.clan.lol/clan/clan-core", str(clan_core_flake)
                )
                line = line.replace(
                    "https://git.clan.lol/clan/clan-core/archive/main.tar.gz",
                    str(clan_core_flake),
                )
            line = line.replace("__CLAN_SOPS_KEY_PATH__", sops_key)
            line = line.replace("__CLAN_SOPS_KEY_DIR__", str(flake / "facts"))
            buf += line
    print(f"file: {file}")
    print(f"clan_core: {clan_core_flake}")
    print(f"flake: {flake}")
    file.write_text(buf)


class FlakeForTest(NamedTuple):
    path: Path


def set_machine_settings(
    flake: Path,
    machine_name: str,
    machine_settings: dict,
) -> None:
    config_path = flake / "machines" / machine_name / "configuration.json"
    config_path.write_text(json.dumps(machine_settings, indent=2))


def set_git_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_AUTHOR_NAME", "clan-tool")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "clan@example.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "clan-tool")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "clan@example.com")


def init_git(monkeypatch: pytest.MonkeyPatch, flake: Path) -> None:
    set_git_credentials(monkeypatch)
    sp.run(["git", "init", "-b", "main"], cwd=flake, check=True)
    # TODO: Find out why test_vms_api.py fails in nix build
    # but works in pytest when this bottom line is commented out
    sp.run(["git", "add", "."], cwd=flake, check=True)
    sp.run(["git", "commit", "-a", "-m", "Initial commit"], cwd=flake, check=True)


class ClanFlake:
    """
    This class holds all attributes for generating a clan flake.
    For example, inventory and machine configs can be set via self.inventory and self.machines["my_machine"] = {...}.
    Whenever a flake's configuration is changed, it needs to be re-generated by calling refresh().

    This class can also be used for managing templates.
    Once initialized, all its settings including all generated files, if any, can be copied using the copy() method.
    This avoids expensive re-computation, like for example creating the flake.lock over and over again.
    """

    def __init__(
        self,
        temporary_home: Path,
        flake_template: Path,
        suppress_tmp_home_warning: bool = False,
    ) -> None:
        self._flake_template = flake_template
        self.inventory = nested_dict()
        self.machines = nested_dict()
        self.substitutions: dict[str, str] = {
            "git+https://git.clan.lol/clan/clan-core": "path://" + str(CLAN_CORE),
            "https://git.clan.lol/clan/clan-core/archive/main.tar.gz": "path://"
            + str(CLAN_CORE),
        }
        self.clan_modules: list[str] = []
        self.temporary_home = temporary_home
        self.path = temporary_home / "flake"
        if not suppress_tmp_home_warning:
            if "/tmp" not in str(os.environ.get("HOME")):
                log.warning(
                    f"!! $HOME does not point to a temp directory!! HOME={os.environ['HOME']}"
                )

    def copy(
        self,
        temporary_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> "ClanFlake":
        # copy the files to the new location
        shutil.copytree(self.path, temporary_home / "flake")
        set_git_credentials(monkeypatch)
        return ClanFlake(
            temporary_home=temporary_home,
            flake_template=self._flake_template,
        )

    def substitute(self) -> None:
        for file in self.path.rglob("*"):
            if ".git" in file.parts:
                continue
            if file.is_file():
                buf = ""
                with file.open() as f:
                    for line in f:
                        for key, value in self.substitutions.items():
                            line = line.replace(key, value)
                        buf += line
                file.write_text(buf)

    def init_from_template(self) -> None:
        shutil.copytree(self._flake_template, self.path)
        sp.run(["chmod", "+w", "-R", str(self.path)], check=True)
        self.substitute()
        if not (self.path / ".git").exists():
            with locked_open(Path(lock_nix), "w"):
                sp.run(
                    [
                        "nix",
                        "flake",
                        "lock",
                        "--extra-experimental-features",
                        "flakes nix-command",
                    ],
                    cwd=self.path,
                    check=True,
                )
                with pytest.MonkeyPatch.context() as mp:
                    init_git(mp, self.path)

    def refresh(self) -> None:
        if not self.path.exists():
            self.init_from_template()
        self.substitute()
        if self.inventory:
            inventory_path = self.path / "inventory.json"
            inventory_path.write_text(json.dumps(self.inventory, indent=2))
        imports = "\n".join(
            [f"clan-core.clanModules.{module}" for module in self.clan_modules]
        )
        for machine_name, machine_config in self.machines.items():
            configuration_nix = (
                self.path / "machines" / machine_name / "configuration.nix"
            )
            configuration_nix.parent.mkdir(parents=True, exist_ok=True)
            configuration_nix.write_text(f"""
                {{clan-core, ...}}:
                {{
                    imports = [
                        (builtins.fromJSON (builtins.readFile ./configuration.json))
                        {imports}
                    ];
                }}
            """)
            set_machine_settings(self.path, machine_name, machine_config)
        sp.run(["git", "add", "."], cwd=self.path, check=True)
        sp.run(
            ["git", "commit", "-a", "-m", "Update by flake generator"],
            cwd=self.path,
            check=True,
        )


@pytest.fixture(scope="session")
def minimal_flake_template() -> Iterator[ClanFlake]:
    with (
        tempfile.TemporaryDirectory(prefix="flake-") as home,
        pytest.MonkeyPatch.context() as mp,
    ):
        mp.setenv("HOME", home)
        flake = ClanFlake(
            temporary_home=Path(home),
            flake_template=CLAN_CORE / "templates" / "minimal",
        )
        flake.init_from_template()
        yield flake


@pytest.fixture
def flake(
    temporary_home: Path,
    minimal_flake_template: ClanFlake,
    monkeypatch: pytest.MonkeyPatch,
) -> ClanFlake:
    return minimal_flake_template.copy(temporary_home, monkeypatch)


def create_flake(
    temporary_home: Path,
    flake_template: str | Path,
    monkeypatch: pytest.MonkeyPatch,
    clan_core_flake: Path | None = None,
    # names referring to pre-defined machines from ../machines
    machines: list[str] | None = None,
    # alternatively specify the machines directly including their config
    machine_configs: dict[str, dict] | None = None,
    remote: bool = False,
) -> Iterator[FlakeForTest]:
    """
    Creates a flake with the given name and machines.
    The machine names map to the machines in ./test_machines
    """
    if machine_configs is None:
        machine_configs = {}
    if machines is None:
        machines = []
    if isinstance(flake_template, Path):
        template_path = flake_template
    else:
        template_path = Path(__file__).parent / flake_template

    flake_template_name = template_path.name

    # copy the template to a new temporary location
    flake = temporary_home / flake_template_name
    shutil.copytree(template_path, flake)
    sp.run(["chmod", "+w", "-R", str(flake)], check=True)

    # add the requested machines to the flake
    if machines:
        (flake / "machines").mkdir(parents=True, exist_ok=True)
    for machine_name in machines:
        machine_path = Path(__file__).parent / "machines" / machine_name
        shutil.copytree(machine_path, flake / "machines" / machine_name)
        substitute(flake / "machines" / machine_name / "default.nix", flake)

    # generate machines from machineConfigs
    for machine_name, machine_config in machine_configs.items():
        settings_path = flake / "machines" / machine_name / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(machine_config, indent=2))

    # in the flake.nix file replace the string __CLAN_URL__ with the the clan flake
    # provided by get_test_flake_toplevel
    flake_nix = flake / "flake.nix"
    # this is where we would install the sops key to, when updating
    substitute(flake_nix, clan_core_flake, flake)

    if "/tmp" not in str(os.environ.get("HOME")):
        log.warning(
            f"!! $HOME does not point to a temp directory!! HOME={os.environ['HOME']}"
        )

    init_git(monkeypatch, flake)

    if remote:
        with tempfile.TemporaryDirectory(prefix="flake-"):
            yield FlakeForTest(flake)
    else:
        yield FlakeForTest(flake)


@pytest.fixture
def test_flake(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    yield from create_flake(
        temporary_home=temporary_home,
        flake_template="test_flake",
        monkeypatch=monkeypatch,
    )
    # check that git diff on ./sops is empty
    if (temporary_home / "test_flake" / "sops").exists():
        git_proc = sp.run(
            ["git", "diff", "--exit-code", "./sops"],
            cwd=temporary_home / "test_flake",
            stderr=sp.PIPE,
            check=False,
        )
        if git_proc.returncode != 0:
            log.error(git_proc.stderr.decode())
            msg = "git diff on ./sops is not empty. This should not happen as all changes should be committed"
            raise FixtureError(msg)


@pytest.fixture
def test_flake_with_core(
    monkeypatch: pytest.MonkeyPatch, temporary_home: Path
) -> Iterator[FlakeForTest]:
    if not (CLAN_CORE / "flake.nix").exists():
        msg = "clan-core flake not found. This test requires the clan-core flake to be present"
        raise FixtureError(msg)
    yield from create_flake(
        temporary_home=temporary_home,
        flake_template="test_flake_with_core",
        clan_core_flake=CLAN_CORE,
        monkeypatch=monkeypatch,
    )
