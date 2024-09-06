import json
from pathlib import Path

import pytest
from age_keys import SopsSetup
from clan_cli.nix import nix_eval, run
from fixtures_flakes import generate_flake
from helpers import cli
from helpers.nixos_config import nested_dict
from helpers.vms import qga_connect, run_vm_in_thread, wait_vm_down
from root import CLAN_CORE


@pytest.mark.impure
def test_vm_deployment(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
    sops_setup: SopsSetup,
) -> None:
    config = nested_dict()
    config["clan"]["virtualisation"]["graphics"] = False
    config["services"]["getty"]["autologinUser"] = "root"
    config["services"]["openssh"]["enable"] = True
    config["networking"]["firewall"]["enable"] = False
    my_generator = config["clan"]["core"]["vars"]["generators"]["my_generator"]
    my_generator["files"]["my_secret"]["secret"] = True
    my_generator["script"] = """
        echo hello > $out/my_secret
    """
    my_shared_generator = config["clan"]["core"]["vars"]["generators"][
        "my_shared_generator"
    ]
    my_shared_generator["share"] = True
    my_shared_generator["files"]["shared_secret"]["secret"] = True
    my_shared_generator["files"]["no_deploy_secret"]["secret"] = True
    my_shared_generator["files"]["no_deploy_secret"]["deploy"] = False
    my_shared_generator["script"] = """
        echo hello > $out/shared_secret
        echo hello > $out/no_deploy_secret
    """
    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"my_machine": config},
        monkeypatch=monkeypatch,
    )
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["vars", "generate", "my_machine"])
    # check sops secrets not empty
    sops_secrets = json.loads(
        run(
            nix_eval(
                [
                    f"{flake.path}#nixosConfigurations.my_machine.config.sops.secrets",
                ]
            )
        ).stdout.strip()
    )
    assert sops_secrets != {}
    my_secret_path = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.my_machine.config.clan.core.vars.generators.my_generator.files.my_secret.path",
            ]
        )
    ).stdout.strip()
    assert "no-such-path" not in my_secret_path
    vm = run_vm_in_thread("my_machine")
    qga = qga_connect("my_machine", vm)
    # check my_secret is deployed
    _, out, _ = qga.run("cat /run/secrets/vars/my_generator/my_secret", check=True)
    assert out == "hello\n"
    # check shared_secret is deployed
    _, out, _ = qga.run(
        "cat /run/secrets/vars/my_shared_generator/shared_secret", check=True
    )
    assert out == "hello\n"
    # check no_deploy_secret is not deployed
    returncode, out, _ = qga.run(
        "test -e /run/secrets/vars/my_shared_generator/no_deploy_secret", check=False
    )
    assert returncode != 0
    qga.exec_cmd("poweroff")
    wait_vm_down("my_machine", vm)
