import subprocess
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from age_keys import SopsSetup
from clan_cli.clan_uri import FlakeId
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_shell
from clan_cli.vars.check import check_vars
from clan_cli.vars.list import stringify_all_vars
from clan_cli.vars.public_modules import in_repo
from clan_cli.vars.secret_modules import password_store, sops
from fixtures_flakes import generate_flake
from helpers import cli
from helpers.nixos_config import nested_dict
from root import CLAN_CORE


def test_dependencies_as_files() -> None:
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
    with TemporaryDirectory() as tmpdir:
        dep_tmpdir = Path(tmpdir)
        dependencies_as_dir(decrypted_dependencies, dep_tmpdir)
        assert dep_tmpdir.is_dir()
        assert (dep_tmpdir / "gen_1" / "var_1a").read_bytes() == b"var_1a"
        assert (dep_tmpdir / "gen_1" / "var_1b").read_bytes() == b"var_1b"
        assert (dep_tmpdir / "gen_2" / "var_2a").read_bytes() == b"var_2a"
        assert (dep_tmpdir / "gen_2" / "var_2b").read_bytes() == b"var_2b"
        # ensure the files are not world readable
        assert (dep_tmpdir / "gen_1" / "var_1a").stat().st_mode & 0o777 == 0o600
        assert (dep_tmpdir / "gen_1" / "var_1b").stat().st_mode & 0o777 == 0o600
        assert (dep_tmpdir / "gen_2" / "var_2a").stat().st_mode & 0o777 == 0o600
        assert (dep_tmpdir / "gen_2" / "var_2b").stat().st_mode & 0o777 == 0o600


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
    temporary_home: Path,
) -> None:
    config = nested_dict()
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo hello > $out/my_value"
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    assert not check_vars(machine)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert store.exists("my_generator", "my_value")
    assert store.get("my_generator", "my_value").decode() == "hello\n"
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_value: hello" in vars_text


@pytest.mark.impure
def test_generate_secret_var_sops(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    config = nested_dict()
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = "echo hello > $out/my_secret"
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    machine = Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    assert not check_vars(machine)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
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


@pytest.mark.impure
def test_generate_secret_var_sops_with_default_group(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    config = nested_dict()
    config["clan"]["core"]["sops"]["defaultGroups"] = ["my_group"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = "echo hello > $out/my_secret"
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
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


@pytest.mark.impure
def test_generate_secret_var_password_store(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
) -> None:
    config = nested_dict()
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
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    gnupghome = temporary_home / "gpg"
    gnupghome.mkdir(mode=0o700)
    monkeypatch.setenv("GNUPGHOME", str(gnupghome))
    monkeypatch.setenv("PASSWORD_STORE_DIR", str(temporary_home / "pass"))
    gpg_key_spec = temporary_home / "gpg_key_spec"
    gpg_key_spec.write_text(
        """
        Key-Type: 1
        Key-Length: 1024
        Name-Real: Root Superuser
        Name-Email: test@local
        Expire-Date: 0
        %no-protection
    """
    )
    subprocess.run(
        nix_shell(
            ["nixpkgs#gnupg"], ["gpg", "--batch", "--gen-key", str(gpg_key_spec)]
        ),
        check=True,
    )
    subprocess.run(
        nix_shell(["nixpkgs#pass"], ["pass", "init", "test@local"]), check=True
    )
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
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    machine1_config = nested_dict()
    machine1_generator = machine1_config["clan"]["core"]["vars"]["generators"][
        "my_generator"
    ]
    machine1_generator["files"]["my_secret"]["secret"] = True
    machine1_generator["files"]["my_value"]["secret"] = False
    machine1_generator["script"] = (
        "echo machine1 > $out/my_secret && echo machine1 > $out/my_value"
    )
    machine2_config = nested_dict()
    machine2_generator = machine2_config["clan"]["core"]["vars"]["generators"][
        "my_generator"
    ]
    machine2_generator["files"]["my_secret"]["secret"] = True
    machine2_generator["files"]["my_value"]["secret"] = False
    machine2_generator["script"] = (
        "echo machine2 > $out/my_secret && echo machine2 > $out/my_value"
    )
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"machine1": machine1_config, "machine2": machine2_config},
        monkeypatch=monkeypatch,
    )
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
    temporary_home: Path,
) -> None:
    config = nested_dict()
    parent_gen = config["clan"]["core"]["vars"]["generators"]["parent_generator"]
    parent_gen["files"]["my_value"]["secret"] = False
    parent_gen["script"] = "echo hello > $out/my_value"
    child_gen = config["clan"]["core"]["vars"]["generators"]["child_generator"]
    child_gen["files"]["my_value"]["secret"] = False
    child_gen["dependencies"] = ["parent_generator"]
    child_gen["script"] = "cat $in/parent_generator/my_value > $out/my_value"
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
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
    temporary_home: Path,
    prompt_type: str,
    input_value: str,
) -> None:
    config = nested_dict()
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["prompts"]["prompt1"]["description"] = "dream2nix"
    my_generator["prompts"]["prompt1"]["createFile"] = False
    my_generator["prompts"]["prompt1"]["type"] = prompt_type
    my_generator["script"] = "cat $prompts/prompt1 > $out/my_value"
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    monkeypatch.setattr("sys.stdin", StringIO(input_value))
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=FlakeId(str(flake.path)))
    )
    assert in_repo_store.exists("my_generator", "my_value")
    assert in_repo_store.get("my_generator", "my_value").decode() == input_value


@pytest.mark.impure
def test_share_flag(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    config = nested_dict()
    shared_generator = config["clan"]["core"]["vars"]["generators"]["shared_generator"]
    shared_generator["files"]["my_secret"]["secret"] = True
    shared_generator["files"]["my_value"]["secret"] = False
    shared_generator["script"] = (
        "echo hello > $out/my_secret && echo hello > $out/my_value"
    )
    shared_generator["share"] = True
    unshared_generator = config["clan"]["core"]["vars"]["generators"][
        "unshared_generator"
    ]
    unshared_generator["files"]["my_secret"]["secret"] = True
    unshared_generator["files"]["my_value"]["secret"] = False
    unshared_generator["script"] = (
        "echo hello > $out/my_secret && echo hello > $out/my_value"
    )
    unshared_generator["share"] = False
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
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


@pytest.mark.impure
def test_prompt_create_file(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    """
    Test that the createFile flag in the prompt configuration works as expected
    """
    config = nested_dict()
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["createFile"] = True
    my_generator["prompts"]["prompt2"]["createFile"] = False
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    monkeypatch.setattr("sys.stdin", StringIO("input1\ninput2\n"))
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
    temporary_home: Path,
) -> None:
    from clan_cli.vars.list import get_prompts

    config = nested_dict()
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["type"] = "line"
    my_generator["files"]["prompt1"]["secret"] = False
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    monkeypatch.setattr("sys.stdin", StringIO("input1"))
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
    temporary_home: Path,
) -> None:
    from clan_cli.vars._types import GeneratorUpdate
    from clan_cli.vars.list import set_prompts

    config = nested_dict()
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["type"] = "line"
    my_generator["files"]["prompt1"]["secret"] = False
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
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
