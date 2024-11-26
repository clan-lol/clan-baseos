import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from age_keys import SopsSetup
from clan_cli.clan_uri import FlakeId
from clan_cli.errors import ClanError
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_eval, run
from clan_cli.vars.check import check_vars
from clan_cli.vars.generate import generate_vars_for_machine
from clan_cli.vars.get import get_var
from clan_cli.vars.list import stringify_all_vars
from clan_cli.vars.public_modules import in_repo
from clan_cli.vars.secret_modules import password_store, sops
from clan_cli.vars.set import set_var
from fixtures_flakes import ClanFlake
from helpers import cli
from stdout import CaptureOutput


def test_dependencies_as_files(temp_dir: Path) -> None:
    from clan_cli.vars.generate import dependencies_as_dir

    decrypted_dependencies = {
        "gen_1": {
            "var_1a": b"var_1a",
            "var_1b": b"var_1b",
        },
        "gen_2": {
            "var_2a": b"var_2a",
            "var_2b": b"var_2b",
        },
    }
    dependencies_as_dir(decrypted_dependencies, temp_dir)
    assert temp_dir.is_dir()
    assert (temp_dir / "gen_1" / "var_1a").read_bytes() == b"var_1a"
    assert (temp_dir / "gen_1" / "var_1b").read_bytes() == b"var_1b"
    assert (temp_dir / "gen_2" / "var_2a").read_bytes() == b"var_2a"
    assert (temp_dir / "gen_2" / "var_2b").read_bytes() == b"var_2b"
    # ensure the files are not world readable
    assert (temp_dir / "gen_1" / "var_1a").stat().st_mode & 0o777 == 0o600
    assert (temp_dir / "gen_1" / "var_1b").stat().st_mode & 0o777 == 0o600
    assert (temp_dir / "gen_2" / "var_2a").stat().st_mode & 0o777 == 0o600
    assert (temp_dir / "gen_2" / "var_2b").stat().st_mode & 0o777 == 0o600


def test_required_generators() -> None:
    from clan_cli.vars.graph import all_missing_closure, requested_closure

    @dataclass
    class Generator:
        dependencies: list[str]
        exists: bool  # result is already on disk

    generators = {
        "gen_1": Generator([], True),
        "gen_2": Generator(["gen_1"], False),
        "gen_2a": Generator(["gen_2"], False),
        "gen_2b": Generator(["gen_2"], True),
    }

    assert requested_closure(["gen_1"], generators) == [
        "gen_1",
        "gen_2",
        "gen_2a",
        "gen_2b",
    ]
    assert requested_closure(["gen_2"], generators) == ["gen_2", "gen_2a", "gen_2b"]
    assert requested_closure(["gen_2a"], generators) == ["gen_2", "gen_2a", "gen_2b"]
    assert requested_closure(["gen_2b"], generators) == ["gen_2", "gen_2a", "gen_2b"]

    assert all_missing_closure(generators) == ["gen_2", "gen_2a", "gen_2b"]


@pytest.mark.impure
def test_generate_public_var(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo hello > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    assert not check_vars(machine)
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_value: <not set>" in vars_text
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert store.exists("my_generator", "my_value")
    assert store.get("my_generator", "my_value").decode() == "hello\n"
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_value: hello" in vars_text
    vars_eval = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.my_value.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(vars_eval) == "hello\n"


@pytest.mark.impure
def test_generate_secret_var_sops(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = "echo hello > $out/my_secret"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    assert not check_vars(machine)
    vars_text = stringify_all_vars(machine)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    assert "my_generator/my_secret: <not set>" in vars_text
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert not in_repo_store.exists("my_generator", "my_secret")
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert sops_store.exists("my_generator", "my_secret")
    assert sops_store.get("my_generator", "my_secret").decode() == "hello\n"
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_secret" in vars_text
    # test regeneration works
    cli.run(
        ["vars", "generate", "--flake", str(flake.path), "my_machine", "--regenerate"]
    )


# TODO: it doesn't actually test if the group has access
@pytest.mark.impure
def test_generate_secret_var_sops_with_default_group(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    config["clan"]["core"]["sops"]["defaultGroups"] = ["my_group"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = "echo hello > $out/my_secret"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["secrets", "groups", "add-user", "my_group", sops_setup.user])
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert not in_repo_store.exists("my_generator", "my_secret")
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert sops_store.exists("my_generator", "my_secret")
    assert sops_store.get("my_generator", "my_secret").decode() == "hello\n"
    # add another user and check if secret gets re-encrypted
    from clan_cli.secrets.sops import generate_private_key

    _, pubkey_uschi = generate_private_key()
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(flake.path),
            "uschi",
            pubkey_uschi,
        ]
    )
    cli.run(["secrets", "groups", "add-user", "my_group", "uschi"])
    with pytest.raises(ClanError):
        cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    # apply fix
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine", "--fix"])
    # check if new user can access the secret
    monkeypatch.setenv("USER", "uschi")
    assert sops_store.user_has_access(
        "uschi", "my_generator", "my_secret", shared=False
    )


@pytest.mark.impure
def test_generated_shared_secret_sops(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    m1_config = flake.machines["machine1"]
    m1_config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    shared_generator = m1_config["clan"]["core"]["vars"]["generators"][
        "my_shared_generator"
    ]
    shared_generator["share"] = True
    shared_generator["files"]["my_shared_secret"]["secret"] = True
    shared_generator["script"] = "echo hello > $out/my_shared_secret"
    m2_config = flake.machines["machine2"]
    m2_config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    m2_config["clan"]["core"]["vars"]["generators"]["my_shared_generator"] = (
        shared_generator.copy()
    )
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    machine1 = Machine(name="machine1", flake=FlakeId(str(flake.path)))
    machine2 = Machine(name="machine2", flake=FlakeId(str(flake.path)))
    cli.run(["vars", "generate", "--flake", str(flake.path), "machine1"])
    assert check_vars(machine1)
    cli.run(["vars", "generate", "--flake", str(flake.path), "machine2"])
    assert check_vars(machine2)
    assert check_vars(machine2)
    m1_sops_store = sops.SecretStore(machine1)
    m2_sops_store = sops.SecretStore(machine2)
    assert m1_sops_store.exists("my_shared_generator", "my_shared_secret", shared=True)
    assert m2_sops_store.exists("my_shared_generator", "my_shared_secret", shared=True)
    assert m1_sops_store.machine_has_access(
        "my_shared_generator", "my_shared_secret", shared=True
    )
    assert m2_sops_store.machine_has_access(
        "my_shared_generator", "my_shared_secret", shared=True
    )


@pytest.mark.impure
def test_generate_secret_var_password_store(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    test_root: Path,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    config["clan"]["core"]["vars"]["settings"]["secretStore"] = "password-store"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = "echo hello > $out/my_secret"
    my_shared_generator = config["clan"]["core"]["vars"]["generators"][
        "my_shared_generator"
    ]
    my_shared_generator["share"] = True
    my_shared_generator["files"]["my_shared_secret"]["secret"] = True
    my_shared_generator["script"] = "echo hello > $out/my_shared_secret"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    gnupghome = flake.path / "gpg"
    shutil.copytree(test_root / "data" / "gnupg-home", gnupghome)
    monkeypatch.setenv("GNUPGHOME", str(gnupghome))

    password_store_dir = flake.path / "pass"
    shutil.copytree(test_root / "data" / "password-store", password_store_dir)
    monkeypatch.setenv("PASSWORD_STORE_DIR", str(flake.path / "pass"))

    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    assert not check_vars(machine)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    store = password_store.SecretStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert store.exists("my_generator", "my_secret", shared=False)
    assert not store.exists("my_generator", "my_secret", shared=True)
    assert store.exists("my_shared_generator", "my_shared_secret", shared=True)
    assert not store.exists("my_shared_generator", "my_shared_secret", shared=False)
    assert store.get("my_generator", "my_secret", shared=False).decode() == "hello\n"
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_secret" in vars_text


@pytest.mark.impure
def test_generate_secret_for_multiple_machines(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    machine1_config = flake.machines["machine1"]
    machine1_generator = machine1_config["clan"]["core"]["vars"]["generators"][
        "my_generator"
    ]
    machine1_generator["files"]["my_secret"]["secret"] = True
    machine1_generator["files"]["my_value"]["secret"] = False
    machine1_generator["script"] = (
        "echo machine1 > $out/my_secret && echo machine1 > $out/my_value"
    )
    machine2_config = flake.machines["machine2"]
    machine2_generator = machine2_config["clan"]["core"]["vars"]["generators"][
        "my_generator"
    ]
    machine2_generator["files"]["my_secret"]["secret"] = True
    machine2_generator["files"]["my_value"]["secret"] = False
    machine2_generator["script"] = (
        "echo machine2 > $out/my_secret && echo machine2 > $out/my_value"
    )
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["vars", "generate", "--flake", str(flake.path)])
    # check if public vars have been created correctly
    in_repo_store1 = in_repo.FactStore(
        Machine(name="machine1", flake=FlakeId(str(flake.path)))
    )
    in_repo_store2 = in_repo.FactStore(
        Machine(name="machine2", flake=FlakeId(str(flake.path)))
    )
    assert in_repo_store1.exists("my_generator", "my_value")
    assert in_repo_store2.exists("my_generator", "my_value")
    assert in_repo_store1.get("my_generator", "my_value").decode() == "machine1\n"
    assert in_repo_store2.get("my_generator", "my_value").decode() == "machine2\n"
    # check if secret vars have been created correctly
    sops_store1 = sops.SecretStore(
        Machine(name="machine1", flake=FlakeId(str(flake.path)))
    )
    sops_store2 = sops.SecretStore(
        Machine(name="machine2", flake=FlakeId(str(flake.path)))
    )
    assert sops_store1.exists("my_generator", "my_secret")
    assert sops_store2.exists("my_generator", "my_secret")
    assert sops_store1.get("my_generator", "my_secret").decode() == "machine1\n"
    assert sops_store2.get("my_generator", "my_secret").decode() == "machine2\n"


@pytest.mark.impure
def test_dependant_generators(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    config = flake.machines["my_machine"]
    parent_gen = config["clan"]["core"]["vars"]["generators"]["parent_generator"]
    parent_gen["files"]["my_value"]["secret"] = False
    parent_gen["script"] = "echo hello > $out/my_value"
    child_gen = config["clan"]["core"]["vars"]["generators"]["child_generator"]
    child_gen["files"]["my_value"]["secret"] = False
    child_gen["dependencies"] = ["parent_generator"]
    child_gen["script"] = "cat $in/parent_generator/my_value > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert in_repo_store.exists("parent_generator", "my_value")
    assert in_repo_store.get("parent_generator", "my_value").decode() == "hello\n"
    assert in_repo_store.exists("child_generator", "my_value")
    assert in_repo_store.get("child_generator", "my_value").decode() == "hello\n"


@pytest.mark.impure
@pytest.mark.parametrize(
    ("prompt_type", "input_value"),
    [
        ("line", "my input"),
        ("multiline", "my\nmultiline\ninput\n"),
        # The hidden type cannot easily be tested, as getpass() reads from /dev/tty directly
        # ("hidden", "my hidden input"),
    ],
)
def test_prompt(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    prompt_type: str,
    input_value: str,
) -> None:
    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["prompts"]["prompt1"]["description"] = "dream2nix"
    my_generator["prompts"]["prompt1"]["createFile"] = False
    my_generator["prompts"]["prompt1"]["type"] = prompt_type
    my_generator["script"] = "cat $prompts/prompt1 > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    monkeypatch.setattr(
        "clan_cli.vars.prompt.MOCK_PROMPT_RESPONSE", iter([input_value])
    )
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert in_repo_store.exists("my_generator", "my_value")
    assert in_repo_store.get("my_generator", "my_value").decode() == input_value


@pytest.mark.impure
def test_share_flag(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    shared_generator = config["clan"]["core"]["vars"]["generators"]["shared_generator"]
    shared_generator["share"] = True
    shared_generator["files"]["my_secret"]["secret"] = True
    shared_generator["files"]["my_value"]["secret"] = False
    shared_generator["script"] = (
        "echo hello > $out/my_secret && echo hello > $out/my_value"
    )
    unshared_generator = config["clan"]["core"]["vars"]["generators"][
        "unshared_generator"
    ]
    unshared_generator["share"] = False
    unshared_generator["files"]["my_secret"]["secret"] = True
    unshared_generator["files"]["my_value"]["secret"] = False
    unshared_generator["script"] = (
        "echo hello > $out/my_secret && echo hello > $out/my_value"
    )
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    assert not check_vars(machine)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    # check secrets stored correctly
    assert sops_store.exists("shared_generator", "my_secret", shared=True)
    assert not sops_store.exists("shared_generator", "my_secret", shared=False)
    assert sops_store.exists("unshared_generator", "my_secret", shared=False)
    assert not sops_store.exists("unshared_generator", "my_secret", shared=True)
    # check values stored correctly
    assert in_repo_store.exists("shared_generator", "my_value", shared=True)
    assert not in_repo_store.exists("shared_generator", "my_value", shared=False)
    assert in_repo_store.exists("unshared_generator", "my_value", shared=False)
    assert not in_repo_store.exists("unshared_generator", "my_value", shared=True)
    vars_eval = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.shared_generator.files.my_value.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(vars_eval) == "hello\n"


@pytest.mark.impure
def test_depending_on_shared_secret_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    shared_generator = config["clan"]["core"]["vars"]["generators"]["shared_generator"]
    shared_generator["share"] = True
    shared_generator["files"]["my_secret"]["secret"] = True
    shared_generator["script"] = "echo hello > $out/my_secret"
    dependent_generator = config["clan"]["core"]["vars"]["generators"][
        "dependent_generator"
    ]
    dependent_generator["share"] = False
    dependent_generator["files"]["my_secret"]["secret"] = True
    dependent_generator["dependencies"] = ["shared_generator"]
    dependent_generator["script"] = (
        "cat $in/shared_generator/my_secret > $out/my_secret"
    )
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])


@pytest.mark.impure
def test_prompt_create_file(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    """
    Test that the createFile flag in the prompt configuration works as expected
    """
    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["createFile"] = True
    my_generator["prompts"]["prompt2"]["createFile"] = False
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    monkeypatch.setattr(
        "clan_cli.vars.prompt.MOCK_PROMPT_RESPONSE", iter(["input1", "input2"])
    )
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert sops_store.exists("my_generator", "prompt1")
    assert not sops_store.exists("my_generator", "prompt2")
    assert sops_store.get("my_generator", "prompt1").decode() == "input1"


@pytest.mark.impure
def test_api_get_prompts(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    from clan_cli.vars.list import get_prompts

    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["type"] = "line"
    my_generator["files"]["prompt1"]["secret"] = False
    flake.refresh()
    monkeypatch.chdir(flake.path)
    monkeypatch.setattr("clan_cli.vars.prompt.MOCK_PROMPT_RESPONSE", iter(["input1"]))
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    api_prompts = get_prompts(machine)
    assert len(api_prompts) == 1
    assert api_prompts[0].name == "my_generator"
    assert api_prompts[0].prompts[0].name == "prompt1"
    assert api_prompts[0].prompts[0].previous_value == "input1"


@pytest.mark.impure
def test_api_set_prompts(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    from clan_cli.vars._types import GeneratorUpdate
    from clan_cli.vars.list import set_prompts

    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["type"] = "line"
    my_generator["files"]["prompt1"]["secret"] = False
    flake.refresh()
    monkeypatch.chdir(flake.path)
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    set_prompts(
        machine,
        [
            GeneratorUpdate(
                generator="my_generator",
                prompt_values={"prompt1": "input1"},
            )
        ],
    )
    store = in_repo.FactStore(machine)
    assert store.exists("my_generator", "prompt1")
    assert store.get("my_generator", "prompt1").decode() == "input1"
    set_prompts(
        machine,
        [
            GeneratorUpdate(
                generator="my_generator",
                prompt_values={"prompt1": "input2"},
            )
        ],
    )
    assert store.get("my_generator", "prompt1").decode() == "input2"


@pytest.mark.impure
def test_commit_message(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo hello > $out/my_value"
    my_secret_generator = config["clan"]["core"]["vars"]["generators"][
        "my_secret_generator"
    ]
    my_secret_generator["files"]["my_secret"]["secret"] = True
    my_secret_generator["script"] = "echo hello > $out/my_secret"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(
        [
            "vars",
            "generate",
            "--flake",
            str(flake.path),
            "my_machine",
            "--service",
            "my_generator",
        ]
    )
    # get last commit message
    commit_message = run(
        ["git", "log", "-1", "--pretty=%B"],
    ).stdout.strip()
    assert (
        commit_message
        == "Update vars via generator my_generator for machine my_machine"
    )
    cli.run(
        [
            "vars",
            "generate",
            "--flake",
            str(flake.path),
            "my_machine",
            "--service",
            "my_secret_generator",
        ]
    )
    commit_message = run(
        ["git", "log", "-1", "--pretty=%B"],
    ).stdout.strip()
    assert (
        commit_message
        == "Update vars via generator my_secret_generator for machine my_machine"
    )


@pytest.mark.impure
def test_default_value(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["files"]["my_value"]["value"]["_type"] = "override"
    my_generator["files"]["my_value"]["value"]["priority"] = 1000  # mkDefault
    my_generator["files"]["my_value"]["value"]["content"] = "foo"
    my_generator["script"] = "echo -n hello > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    # ensure evaluating the default value works without generating the value
    value_eval = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.my_value.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(value_eval) == "foo"
    # generate
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    # ensure the value is set correctly
    value_eval = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.my_value.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(value_eval) == "hello"


@pytest.mark.impure
def test_stdout_of_generate(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    capture_output: CaptureOutput,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo -n hello > $out/my_value"
    my_secret_generator = config["clan"]["core"]["vars"]["generators"][
        "my_secret_generator"
    ]
    my_secret_generator["files"]["my_secret"]["secret"] = True
    my_secret_generator["script"] = "echo -n hello > $out/my_secret"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    from clan_cli.vars.generate import generate_vars_for_machine

    with capture_output as output:
        generate_vars_for_machine(
            Machine(name="my_machine", flake=FlakeId(str(flake.path))),
            "my_generator",
            regenerate=False,
            fix=False,
        )

    assert "Updated var my_generator/my_value" in output.out
    assert "old: <not set>" in output.out
    assert "new: hello" in output.out
    set_var("my_machine", "my_generator/my_value", b"world", FlakeId(str(flake.path)))
    with capture_output as output:
        generate_vars_for_machine(
            Machine(name="my_machine", flake=FlakeId(str(flake.path))),
            "my_generator",
            regenerate=True,
            fix=False,
        )
    assert "Updated var my_generator/my_value" in output.out
    assert "old: world" in output.out
    assert "new: hello" in output.out
    # check the output when nothing gets regenerated
    with capture_output as output:
        generate_vars_for_machine(
            Machine(name="my_machine", flake=FlakeId(str(flake.path))),
            "my_generator",
            regenerate=True,
            fix=False,
        )
    assert "Updated" not in output.out
    assert "hello" in output.out
    with capture_output as output:
        generate_vars_for_machine(
            Machine(name="my_machine", flake=FlakeId(str(flake.path))),
            "my_secret_generator",
            regenerate=False,
            fix=False,
        )
    assert "Updated secret var my_secret_generator/my_secret" in output.out
    assert "hello" not in output.out
    set_var(
        "my_machine",
        "my_secret_generator/my_secret",
        b"world",
        FlakeId(str(flake.path)),
    )
    with capture_output as output:
        generate_vars_for_machine(
            Machine(name="my_machine", flake=FlakeId(str(flake.path))),
            "my_secret_generator",
            regenerate=True,
            fix=False,
        )
    assert "Updated secret var my_secret_generator/my_secret" in output.out
    assert "world" not in output.out
    assert "hello" not in output.out


@pytest.mark.impure
def test_migration_skip(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_service = config["clan"]["core"]["facts"]["services"]["my_service"]
    my_service["secret"]["my_value"] = {}
    my_service["generator"]["script"] = "echo -n hello > $secrets/my_value"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    # the var to migrate to is mistakenly marked as not secret (migration should fail)
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["migrateFact"] = "my_service"
    my_generator["script"] = "echo -n world > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["facts", "generate", "--flake", str(flake.path), "my_machine"])
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert in_repo_store.exists("my_generator", "my_value")
    assert in_repo_store.get("my_generator", "my_value").decode() == "world"


@pytest.mark.impure
def test_migration(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_service = config["clan"]["core"]["facts"]["services"]["my_service"]
    my_service["public"]["my_value"] = {}
    my_service["secret"]["my_secret"] = {}
    my_service["generator"]["script"] = (
        "echo -n hello > $facts/my_value && echo -n hello > $secrets/my_secret"
    )
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["migrateFact"] = "my_service"
    my_generator["script"] = "echo -n world > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["facts", "generate", "--flake", str(flake.path), "my_machine"])
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert in_repo_store.exists("my_generator", "my_value")
    assert in_repo_store.get("my_generator", "my_value").decode() == "hello"
    assert sops_store.exists("my_generator", "my_secret")
    assert sops_store.get("my_generator", "my_secret").decode() == "hello"


@pytest.mark.impure
def test_fails_when_files_are_left_from_other_backend(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_secret_generator = config["clan"]["core"]["vars"]["generators"][
        "my_secret_generator"
    ]
    my_secret_generator["files"]["my_secret"]["secret"] = True
    my_secret_generator["script"] = "echo hello > $out/my_secret"
    my_value_generator = config["clan"]["core"]["vars"]["generators"][
        "my_value_generator"
    ]
    my_value_generator["files"]["my_value"]["secret"] = False
    my_value_generator["script"] = "echo hello > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    for generator in ["my_secret_generator", "my_value_generator"]:
        generate_vars_for_machine(
            Machine(name="my_machine", flake=FlakeId(str(flake.path))),
            generator,
            regenerate=False,
            fix=False,
        )
    my_secret_generator["files"]["my_secret"]["secret"] = False
    my_value_generator["files"]["my_value"]["secret"] = True
    flake.refresh()
    monkeypatch.chdir(flake.path)
    for generator in ["my_secret_generator", "my_value_generator"]:
        with pytest.raises(ClanError):
            generate_vars_for_machine(
                Machine(name="my_machine", flake=FlakeId(str(flake.path))),
                generator,
                regenerate=False,
                fix=False,
            )


@pytest.mark.impure
def test_keygen(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
) -> None:
    monkeypatch.chdir(temporary_home)
    cli.run(["vars", "keygen", "--flake", str(temporary_home), "--user", "user"])
    # check public key exists
    assert (temporary_home / "sops" / "users" / "user").is_dir()
    # check private key exists
    assert (temporary_home / ".config" / "sops" / "age" / "keys.txt").is_file()
    # it should still work, even if the keys already exist
    import shutil

    shutil.rmtree(temporary_home / "sops" / "users" / "user")
    cli.run(["vars", "keygen", "--flake", str(temporary_home), "--user", "user"])
    # check public key exists
    assert (temporary_home / "sops" / "users" / "user").is_dir()


@pytest.mark.impure
def test_vars_get(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo -n hello > $out/my_value"
    my_shared_generator = config["clan"]["core"]["vars"]["generators"][
        "my_shared_generator"
    ]
    my_shared_generator["share"] = True
    my_shared_generator["files"]["my_shared_value"]["secret"] = False
    my_shared_generator["script"] = "echo -n hello > $out/my_shared_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    # get the value of a public var
    assert get_var(machine, "my_generator/my_value").printable_value == "hello"
    assert (
        get_var(machine, "my_shared_generator/my_shared_value").printable_value
        == "hello"
    )


@pytest.mark.impure
def test_invalidation(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    config = flake.machines["my_machine"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo -n $RANDOM > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    value1 = get_var(machine, "my_generator/my_value").printable_value
    # generate again and make sure nothing changes without the invalidation data being set
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    value1_new = get_var(machine, "my_generator/my_value").printable_value
    assert value1 == value1_new
    # set the invalidation data of the generator
    my_generator["invalidationData"] = 1
    flake.refresh()
    # generate again and make sure the value changes
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    value2 = get_var(machine, "my_generator/my_value").printable_value
    assert value1 != value2
    # generate again without changing invalidation data -> value should not change
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    value2_new = get_var(machine, "my_generator/my_value").printable_value
    assert value2 == value2_new
