import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from age_keys import SopsSetup
from clan_cli.errors import ClanError
from clan_cli.flake import Flake
from clan_cli.machines.machines import Machine
from clan_cli.nix import nix_eval, run
from clan_cli.vars.check import check_vars
from clan_cli.vars.generate import Generator, generate_vars_for_machine
from clan_cli.vars.get import get_var
from clan_cli.vars.graph import all_missing_closure, requested_closure
from clan_cli.vars.list import stringify_all_vars
from clan_cli.vars.public_modules import in_repo
from clan_cli.vars.secret_modules import password_store, sops
from clan_cli.vars.set import set_var
from fixtures_flakes import ClanFlake
from helpers import cli

if TYPE_CHECKING:
    from age_keys import KeyPair


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
    gen_1 = Generator(name="gen_1", dependencies=[])
    gen_2 = Generator(name="gen_2", dependencies=["gen_1"])
    gen_2a = Generator(name="gen_2a", dependencies=["gen_2"])
    gen_2b = Generator(name="gen_2b", dependencies=["gen_2"])

    gen_1.exists = True
    gen_2.exists = False
    gen_2a.exists = False
    gen_2b.exists = True
    generators = {
        generator.name: generator for generator in [gen_1, gen_2, gen_2a, gen_2b]
    }

    def generator_names(generator: list[Generator]) -> list[str]:
        return [gen.name for gen in generator]

    assert generator_names(requested_closure(["gen_1"], generators)) == [
        "gen_1",
        "gen_2",
        "gen_2a",
        "gen_2b",
    ]
    assert generator_names(requested_closure(["gen_2"], generators)) == [
        "gen_2",
        "gen_2a",
        "gen_2b",
    ]
    assert generator_names(requested_closure(["gen_2a"], generators)) == [
        "gen_2",
        "gen_2a",
        "gen_2b",
    ]
    assert generator_names(requested_closure(["gen_2b"], generators)) == [
        "gen_2",
        "gen_2a",
        "gen_2b",
    ]

    assert generator_names(all_missing_closure(generators)) == [
        "gen_2",
        "gen_2a",
        "gen_2b",
    ]


@pytest.mark.with_core
def test_generate_public_and_secret_vars(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = (
        "echo -n public > $out/my_value; echo -n secret > $out/my_secret; echo -n non-default > $out/value_with_default"
    )

    my_generator["files"]["value_with_default"]["secret"] = False
    my_generator["files"]["value_with_default"]["value"]["_type"] = "override"
    my_generator["files"]["value_with_default"]["value"]["priority"] = 1000  # mkDefault
    my_generator["files"]["value_with_default"]["value"]["content"] = "default_value"

    my_shared_generator = config["clan"]["core"]["vars"]["generators"][
        "my_shared_generator"
    ]
    my_shared_generator["share"] = True
    my_shared_generator["files"]["my_shared_value"]["secret"] = False
    my_shared_generator["script"] = "echo -n shared > $out/my_shared_value"

    dependent_generator = config["clan"]["core"]["vars"]["generators"][
        "dependent_generator"
    ]
    dependent_generator["share"] = False
    dependent_generator["files"]["my_secret"]["secret"] = True
    dependent_generator["dependencies"] = ["my_shared_generator"]
    dependent_generator["script"] = (
        "cat $in/my_shared_generator/my_shared_value > $out/my_secret"
    )

    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()

    machine = Machine(name="my_machine", flake=Flake(str(flake.path)))
    assert not check_vars(machine)
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_value: <not set>" in vars_text
    assert "my_generator/my_secret: <not set>" in vars_text
    assert "my_shared_generator/my_shared_value: <not set>" in vars_text
    assert "dependent_generator/my_secret: <not set>" in vars_text

    # ensure evaluating the default value works without generating the value
    value_non_default = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.value_with_default.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(value_non_default) == "default_value"

    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    # get last commit message
    commit_message = run(
        ["git", "log", "-3", "--pretty=%B"],
    ).stdout.strip()
    assert (
        "Update vars via generator my_generator for machine my_machine"
        in commit_message
    )
    assert (
        "Update vars via generator my_shared_generator for machine my_machine"
        in commit_message
    )
    assert (
        get_var(
            str(machine.flake.path), machine.name, "my_generator/my_value"
        ).printable_value
        == "public"
    )
    assert (
        get_var(
            str(machine.flake.path), machine.name, "my_shared_generator/my_shared_value"
        ).printable_value
        == "shared"
    )
    vars_text = stringify_all_vars(machine)
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert not in_repo_store.exists(Generator("my_generator"), "my_secret")
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert sops_store.exists(Generator("my_generator"), "my_secret")
    assert sops_store.get(Generator("my_generator"), "my_secret").decode() == "secret"
    assert sops_store.exists(Generator("dependent_generator"), "my_secret")
    assert (
        sops_store.get(Generator("dependent_generator"), "my_secret").decode()
        == "shared"
    )

    assert "my_generator/my_value: public" in vars_text
    assert "my_generator/my_secret" in vars_text
    vars_eval = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.my_value.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(vars_eval) == "public"

    value_non_default = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.value_with_default.value",
            ]
        )
    ).stdout.strip()
    assert json.loads(value_non_default) == "non-default"
    # test regeneration works
    cli.run(
        ["vars", "generate", "--flake", str(flake.path), "my_machine", "--regenerate"]
    )


# TODO: it doesn't actually test if the group has access
@pytest.mark.with_core
def test_generate_secret_var_sops_with_default_group(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
    age_keys: list["KeyPair"],
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    config["clan"]["core"]["sops"]["defaultGroups"] = ["my_group"]
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["files"]["my_public"]["secret"] = False
    my_generator["script"] = (
        "echo hello > $out/my_secret && echo hello > $out/my_public"
    )
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["secrets", "groups", "add-user", "my_group", sops_setup.user])
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert not in_repo_store.exists(Generator("my_generator"), "my_secret")
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert sops_store.exists(Generator("my_generator"), "my_secret")
    assert sops_store.get(Generator("my_generator"), "my_secret").decode() == "hello\n"

    # add another user to the group and check if secret gets re-encrypted
    pubkey_user2 = age_keys[1]
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(flake.path),
            "user2",
            pubkey_user2.pubkey,
        ]
    )
    cli.run(["secrets", "groups", "add-user", "my_group", "user2"])
    # check if new user can access the secret
    monkeypatch.setenv("USER", "user2")
    assert sops_store.user_has_access(
        "user2", Generator("my_generator", share=False), "my_secret"
    )

    # Rotate key of a user
    pubkey_user3 = age_keys[2]
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(flake.path),
            "--force",
            "user2",
            pubkey_user3.pubkey,
        ]
    )
    monkeypatch.setenv("USER", "user2")
    assert sops_store.user_has_access(
        "user2", Generator("my_generator", share=False), "my_secret"
    )


@pytest.mark.with_core
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
    machine1 = Machine(name="machine1", flake=Flake(str(flake.path)))
    machine2 = Machine(name="machine2", flake=Flake(str(flake.path)))
    cli.run(["vars", "generate", "--flake", str(flake.path), "machine1"])
    assert check_vars(machine1)
    cli.run(["vars", "generate", "--flake", str(flake.path), "machine2"])
    assert check_vars(machine2)
    assert check_vars(machine2)
    m1_sops_store = sops.SecretStore(machine1)
    m2_sops_store = sops.SecretStore(machine2)
    assert m1_sops_store.exists(
        Generator("my_shared_generator", share=True), "my_shared_secret"
    )
    assert m2_sops_store.exists(
        Generator("my_shared_generator", share=True), "my_shared_secret"
    )
    assert m1_sops_store.machine_has_access(
        Generator("my_shared_generator", share=True), "my_shared_secret"
    )
    assert m2_sops_store.machine_has_access(
        Generator("my_shared_generator", share=True), "my_shared_secret"
    )


@pytest.mark.with_core
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

    machine = Machine(name="my_machine", flake=Flake(str(flake.path)))
    assert not check_vars(machine)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert check_vars(machine)
    store = password_store.SecretStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert store.exists(Generator("my_generator", share=False, files=[]), "my_secret")
    assert not store.exists(
        Generator("my_generator", share=True, files=[]), "my_secret"
    )
    assert store.exists(
        Generator("my_shared_generator", share=True, files=[]), "my_shared_secret"
    )
    assert not store.exists(
        Generator("my_shared_generator", share=False, files=[]), "my_shared_secret"
    )

    generator = Generator(name="my_generator", share=False, files=[])
    assert store.get(generator, "my_secret").decode() == "hello\n"
    vars_text = stringify_all_vars(machine)
    assert "my_generator/my_secret" in vars_text


@pytest.mark.with_core
def test_generate_secret_for_multiple_machines(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    from clan_cli.nix import nix_config

    local_system = nix_config()["system"]

    machine1_config = flake.machines["machine1"]
    machine1_config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    machine1_generator = machine1_config["clan"]["core"]["vars"]["generators"][
        "my_generator"
    ]
    machine1_generator["files"]["my_secret"]["secret"] = True
    machine1_generator["files"]["my_value"]["secret"] = False
    machine1_generator["script"] = (
        "echo machine1 > $out/my_secret && echo machine1 > $out/my_value"
    )
    machine2_config = flake.machines["machine2"]
    # Test that we can generate secrets for other platforms
    machine2_config["nixpkgs"]["hostPlatform"] = (
        "aarch64-linux" if local_system == "x86_64-linux" else "x86_64-linux"
    )

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
        Machine(name="machine1", flake=Flake(str(flake.path)))
    )
    in_repo_store2 = in_repo.FactStore(
        Machine(name="machine2", flake=Flake(str(flake.path)))
    )
    assert in_repo_store1.exists(Generator("my_generator"), "my_value")
    assert in_repo_store2.exists(Generator("my_generator"), "my_value")
    assert (
        in_repo_store1.get(Generator("my_generator"), "my_value").decode()
        == "machine1\n"
    )
    assert (
        in_repo_store2.get(Generator("my_generator"), "my_value").decode()
        == "machine2\n"
    )
    # check if secret vars have been created correctly
    sops_store1 = sops.SecretStore(
        Machine(name="machine1", flake=Flake(str(flake.path)))
    )
    sops_store2 = sops.SecretStore(
        Machine(name="machine2", flake=Flake(str(flake.path)))
    )
    assert sops_store1.exists(Generator("my_generator"), "my_secret")
    assert sops_store2.exists(Generator("my_generator"), "my_secret")
    assert (
        sops_store1.get(Generator("my_generator"), "my_secret").decode() == "machine1\n"
    )
    assert (
        sops_store2.get(Generator("my_generator"), "my_secret").decode() == "machine2\n"
    )


@pytest.mark.with_core
def test_prompt(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["line_value"]["secret"] = False
    my_generator["files"]["multiline_value"]["secret"] = False

    my_generator["prompts"]["prompt1"]["description"] = "dream2nix"
    my_generator["prompts"]["prompt1"]["persist"] = False
    my_generator["prompts"]["prompt1"]["type"] = "line"

    my_generator["prompts"]["prompt2"]["description"] = "dream2nix"
    my_generator["prompts"]["prompt2"]["persist"] = False
    my_generator["prompts"]["prompt2"]["type"] = "line"

    my_generator["prompts"]["prompt_persist"]["persist"] = True

    my_generator["script"] = (
        "cat $prompts/prompt1 > $out/line_value; cat $prompts/prompt2 > $out/multiline_value"
    )
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    monkeypatch.setattr(
        "clan_cli.vars.prompt.MOCK_PROMPT_RESPONSE",
        iter(["line input", "my\nmultiline\ninput\n", "prompt_persist"]),
    )
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert in_repo_store.exists(Generator("my_generator"), "line_value")
    assert (
        in_repo_store.get(Generator("my_generator"), "line_value").decode()
        == "line input"
    )

    assert in_repo_store.exists(Generator("my_generator"), "multiline_value")
    assert (
        in_repo_store.get(Generator("my_generator"), "multiline_value").decode()
        == "my\nmultiline\ninput\n"
    )
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert sops_store.exists(
        Generator(name="my_generator", share=False, files=[]), "prompt_persist"
    )
    assert (
        sops_store.get(Generator(name="my_generator"), "prompt_persist").decode()
        == "prompt_persist"
    )


@pytest.mark.with_core
def test_multi_machine_shared_vars(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
) -> None:
    """
    Ensure that shared vars are regenerated only when they should, and also can be
    accessed by all machines that should have access.

    Specifically:
        - make sure shared wars are not regenerated when a second machines is added
        - make sure vars can still be accessed by all machines, after they are regenerated
    """
    machine1_config = flake.machines["machine1"]
    machine1_config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    shared_generator = machine1_config["clan"]["core"]["vars"]["generators"][
        "shared_generator"
    ]
    shared_generator["share"] = True
    shared_generator["files"]["my_secret"]["secret"] = True
    shared_generator["files"]["my_value"]["secret"] = False
    shared_generator["script"] = (
        "echo $RANDOM > $out/my_value && echo $RANDOM > $out/my_secret"
    )
    # machine 2 is equivalent to machine 1
    flake.machines["machine2"] = machine1_config
    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    machine1 = Machine(name="machine1", flake=Flake(str(flake.path)))
    machine2 = Machine(name="machine2", flake=Flake(str(flake.path)))
    sops_store_1 = sops.SecretStore(machine1)
    sops_store_2 = sops.SecretStore(machine2)
    in_repo_store_1 = in_repo.FactStore(machine1)
    in_repo_store_2 = in_repo.FactStore(machine2)
    generator = Generator("shared_generator", share=True)
    # generate for machine 1
    cli.run(["vars", "generate", "--flake", str(flake.path), "machine1"])
    # read out values for machine 1
    m1_secret = sops_store_1.get(generator, "my_secret")
    m1_value = in_repo_store_1.get(generator, "my_value")
    # generate for machine 2
    cli.run(["vars", "generate", "--flake", str(flake.path), "machine2"])
    # ensure values are the same for both machines
    assert sops_store_2.get(generator, "my_secret") == m1_secret
    assert in_repo_store_2.get(generator, "my_value") == m1_value

    # ensure shared secret stays available for all machines after regeneration
    # regenerate for machine 1
    cli.run(
        ["vars", "generate", "--flake", str(flake.path), "machine1", "--regenerate"]
    )
    # ensure values changed
    new_secret_1 = sops_store_1.get(generator, "my_secret")
    new_value_1 = in_repo_store_1.get(generator, "my_value")
    new_secret_2 = sops_store_2.get(generator, "my_secret")
    assert new_secret_1 != m1_secret
    assert new_value_1 != m1_value
    # ensure that both machines still have access to the same secret
    assert new_secret_1 == new_secret_2
    assert sops_store_1.machine_has_access(generator, "my_secret")
    assert sops_store_2.machine_has_access(generator, "my_secret")


@pytest.mark.with_core
def test_api_set_prompts(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    from clan_cli.vars._types import GeneratorUpdate
    from clan_cli.vars.list import get_generators, set_prompts

    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["prompts"]["prompt1"]["type"] = "line"
    my_generator["prompts"]["prompt1"]["persist"] = True
    my_generator["files"]["prompt1"]["secret"] = False
    flake.refresh()

    monkeypatch.chdir(flake.path)
    params = {"machine_name": "my_machine", "base_dir": str(flake.path)}

    set_prompts(
        **params,
        updates=[
            GeneratorUpdate(
                generator="my_generator",
                prompt_values={"prompt1": "input1"},
            )
        ],
    )
    machine = Machine(name="my_machine", flake=Flake(str(flake.path)))
    store = in_repo.FactStore(machine)
    assert store.exists(Generator("my_generator"), "prompt1")
    assert store.get(Generator("my_generator"), "prompt1").decode() == "input1"
    set_prompts(
        **params,
        updates=[
            GeneratorUpdate(
                generator="my_generator",
                prompt_values={"prompt1": "input2"},
            )
        ],
    )
    assert store.get(Generator("my_generator"), "prompt1").decode() == "input2"

    generators = get_generators(**params)
    assert len(generators) == 1
    assert generators[0].name == "my_generator"
    assert generators[0].prompts[0].name == "prompt1"
    assert generators[0].prompts[0].previous_value == "input2"


@pytest.mark.with_core
def test_stdout_of_generate(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
    caplog: pytest.LogCaptureFixture,
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

    # with capture_output as output:
    with caplog.at_level(logging.INFO):
        generate_vars_for_machine(
            Machine(name="my_machine", flake=Flake(str(flake.path))),
            "my_generator",
            regenerate=False,
        )

    assert "Updated var my_generator/my_value" in caplog.text
    assert "old: <not set>" in caplog.text
    assert "new: hello" in caplog.text
    caplog.clear()

    set_var("my_machine", "my_generator/my_value", b"world", Flake(str(flake.path)))
    with caplog.at_level(logging.INFO):
        generate_vars_for_machine(
            Machine(name="my_machine", flake=Flake(str(flake.path))),
            "my_generator",
            regenerate=True,
        )
    assert "Updated var my_generator/my_value" in caplog.text
    assert "old: world" in caplog.text
    assert "new: hello" in caplog.text
    caplog.clear()
    # check the output when nothing gets regenerated
    with caplog.at_level(logging.INFO):
        generate_vars_for_machine(
            Machine(name="my_machine", flake=Flake(str(flake.path))),
            "my_generator",
            regenerate=True,
        )
    assert "Updated var" not in caplog.text
    assert "hello" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.INFO):
        generate_vars_for_machine(
            Machine(name="my_machine", flake=Flake(str(flake.path))),
            "my_secret_generator",
            regenerate=False,
        )
    assert "Updated secret var my_secret_generator/my_secret" in caplog.text
    assert "hello" not in caplog.text
    caplog.clear()
    set_var(
        "my_machine",
        "my_secret_generator/my_secret",
        b"world",
        Flake(str(flake.path)),
    )
    with caplog.at_level(logging.INFO):
        generate_vars_for_machine(
            Machine(name="my_machine", flake=Flake(str(flake.path))),
            "my_secret_generator",
            regenerate=True,
        )
    assert "Updated secret var my_secret_generator/my_secret" in caplog.text
    assert "world" not in caplog.text
    assert "hello" not in caplog.text
    caplog.clear()


@pytest.mark.with_core
def test_migration(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
    sops_setup: SopsSetup,
    caplog: pytest.LogCaptureFixture,
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
    my_generator["script"] = "echo -n other > $out/my_value"

    other_service = config["clan"]["core"]["facts"]["services"]["other_service"]
    other_service["secret"]["other_value"] = {}
    other_service["generator"]["script"] = "echo -n hello > $secrets/other_value"
    other_generator = config["clan"]["core"]["vars"]["generators"]["other_generator"]
    # the var to migrate to is mistakenly marked as not secret (migration should fail)
    other_generator["files"]["other_value"]["secret"] = False
    other_generator["migrateFact"] = "my_service"
    other_generator["script"] = "echo -n value-from-vars > $out/other_value"

    flake.refresh()
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["facts", "generate", "--flake", str(flake.path), "my_machine"])
    with caplog.at_level(logging.INFO):
        cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    assert "Migrated var my_generator/my_value" in caplog.text
    assert "Migrated secret var my_generator/my_secret" in caplog.text
    in_repo_store = in_repo.FactStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    sops_store = sops.SecretStore(
        Machine(name="my_machine", flake=Flake(str(flake.path)))
    )
    assert in_repo_store.exists(Generator("my_generator"), "my_value")
    assert in_repo_store.get(Generator("my_generator"), "my_value").decode() == "hello"
    assert sops_store.exists(Generator("my_generator"), "my_secret")
    assert sops_store.get(Generator("my_generator"), "my_secret").decode() == "hello"

    assert in_repo_store.exists(Generator("other_generator"), "other_value")
    assert (
        in_repo_store.get(Generator("other_generator"), "other_value").decode()
        == "value-from-vars"
    )


@pytest.mark.with_core
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
            Machine(name="my_machine", flake=Flake(str(flake.path))),
            generator,
            regenerate=False,
        )
    # Will raise. It was secret before, but now it's not.
    my_secret_generator["files"]["my_secret"]["secret"] = (
        False  # secret -> public (NOT OK)
    )
    # WIll not raise. It was not secret before, and it's secret now.
    my_value_generator["files"]["my_value"]["secret"] = True  # public -> secret (OK)
    flake.refresh()
    monkeypatch.chdir(flake.path)
    for generator in ["my_secret_generator", "my_value_generator"]:
        # This should raise an error
        if generator == "my_secret_generator":
            with pytest.raises(ClanError):
                generate_vars_for_machine(
                    Machine(name="my_machine", flake=Flake(str(flake.path))),
                    generator,
                    regenerate=False,
                )
        else:
            generate_vars_for_machine(
                Machine(name="my_machine", flake=Flake(str(flake.path))),
                generator,
                regenerate=False,
            )


@pytest.mark.with_core
def test_keygen(monkeypatch: pytest.MonkeyPatch, flake: ClanFlake) -> None:
    monkeypatch.chdir(flake.path)
    cli.run(["vars", "keygen", "--flake", str(flake.path), "--user", "user"])
    # check public key exists
    assert (flake.path / "sops" / "users" / "user").is_dir()
    # check private key exists
    assert (flake.temporary_home / ".config" / "sops" / "age" / "keys.txt").is_file()
    # it should still work, even if the keys already exist
    import shutil

    shutil.rmtree(flake.path / "sops" / "users" / "user")
    cli.run(["vars", "keygen", "--flake", str(flake.path), "--user", "user"])
    # check public key exists
    assert (flake.path / "sops" / "users" / "user").is_dir()


@pytest.mark.with_core
def test_invalidation(
    monkeypatch: pytest.MonkeyPatch,
    flake: ClanFlake,
) -> None:
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_value"]["secret"] = False
    my_generator["script"] = "echo -n $RANDOM > $out/my_value"
    flake.refresh()
    monkeypatch.chdir(flake.path)
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    machine = Machine(name="my_machine", flake=Flake(str(flake.path)))
    value1 = get_var(
        str(machine.flake.path), machine.name, "my_generator/my_value"
    ).printable_value
    # generate again and make sure nothing changes without the invalidation data being set
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    value1_new = get_var(
        str(machine.flake.path), machine.name, "my_generator/my_value"
    ).printable_value
    assert value1 == value1_new
    # set the invalidation data of the generator
    my_generator["validation"] = 1
    flake.refresh()
    # generate again and make sure the value changes
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    value2 = get_var(
        str(machine.flake.path), machine.name, "my_generator/my_value"
    ).printable_value
    assert value1 != value2
    # generate again without changing invalidation data -> value should not change
    cli.run(["vars", "generate", "--flake", str(flake.path), "my_machine"])
    value2_new = get_var(
        str(machine.flake.path), machine.name, "my_generator/my_value"
    ).printable_value
    assert value2 == value2_new
