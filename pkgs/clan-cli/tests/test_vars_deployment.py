import json
from pathlib import Path

import pytest
from age_keys import SopsSetup
from clan_cli import cmd
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
    # machine 1
    machine1_config = nested_dict()
    machine1_config["clan"]["virtualisation"]["graphics"] = False
    machine1_config["services"]["getty"]["autologinUser"] = "root"
    machine1_config["services"]["openssh"]["enable"] = True
    machine1_config["networking"]["firewall"]["enable"] = False
    machine1_config["users"]["users"]["root"]["openssh"]["authorizedKeys"]["keys"] = [
        # put your key here when debugging and pass ssh_port in run_vm_in_thread call below
    ]
    m1_generator = machine1_config["clan"]["core"]["vars"]["generators"]["m1_generator"]
    m1_generator["files"]["my_secret"]["secret"] = True
    m1_generator["script"] = """
        echo hello > $out/my_secret
    """
    m1_shared_generator = machine1_config["clan"]["core"]["vars"]["generators"][
        "my_shared_generator"
    ]
    m1_shared_generator["share"] = True
    m1_shared_generator["files"]["shared_secret"]["secret"] = True
    m1_shared_generator["files"]["no_deploy_secret"]["secret"] = True
    m1_shared_generator["files"]["no_deploy_secret"]["deploy"] = False
    m1_shared_generator["script"] = """
        echo hello > $out/shared_secret
        echo hello > $out/no_deploy_secret
    """
    # machine 2
    machine2_config = nested_dict()
    machine2_config["clan"]["virtualisation"]["graphics"] = False
    machine2_config["services"]["getty"]["autologinUser"] = "root"
    machine2_config["services"]["openssh"]["enable"] = True
    machine2_config["users"]["users"]["root"]["openssh"]["authorizedKeys"]["keys"] = [
        # put your key here when debugging and pass ssh_port in run_vm_in_thread call below
    ]
    machine2_config["networking"]["firewall"]["enable"] = False
    machine2_config["clan"]["core"]["vars"]["generators"]["my_shared_generator"] = (
        m1_shared_generator.copy()
    )

    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs={"m1_machine": machine1_config, "m2_machine": machine2_config},
    )
    monkeypatch.chdir(flake.path)
    sops_setup.init()
    cli.run(["vars", "generate"])
    # check sops secrets not empty
    for machine in ["m1_machine", "m2_machine"]:
        sops_secrets = json.loads(
            run(
                nix_eval(
                    [
                        f"{flake.path}#nixosConfigurations.{machine}.config.sops.secrets",
                    ]
                )
            ).stdout.strip()
        )
        assert sops_secrets != {}
    my_secret_path = run(
        nix_eval(
            [
                f"{flake.path}#nixosConfigurations.m1_machine.config.clan.core.vars.generators.m1_generator.files.my_secret.path",
            ]
        )
    ).stdout.strip()
    assert "no-such-path" not in my_secret_path
    for machine in ["m1_machine", "m2_machine"]:
        shared_secret_path = run(
            nix_eval(
                [
                    f"{flake.path}#nixosConfigurations.{machine}.config.clan.core.vars.generators.my_shared_generator.files.shared_secret.path",
                ]
            )
        ).stdout.strip()
        assert "no-such-path" not in shared_secret_path
    # run nix flake lock
    cmd.run(["nix", "flake", "lock"])
    vm_m1 = run_vm_in_thread("m1_machine")
    vm_m2 = run_vm_in_thread("m2_machine")
    with (
        qga_connect("m1_machine", vm_m1) as qga_m1,
        qga_connect("m2_machine", vm_m2) as qga_m2,
    ):
        # check my_secret is deployed
        _, out, _ = qga_m1.run(
            "cat /run/secrets/vars/m1_generator/my_secret", check=True
        )
        assert out == "hello\n"
        # check shared_secret is deployed on m1
        _, out, _ = qga_m1.run(
            "cat /run/secrets/vars/my_shared_generator/shared_secret", check=True
        )
        assert out == "hello\n"
        # check shared_secret is deployed on m2
        _, out, _ = qga_m2.run(
            "cat /run/secrets/vars/my_shared_generator/shared_secret", check=True
        )
        assert out == "hello\n"
        # check no_deploy_secret is not deployed
        returncode, out, _ = qga_m1.run(
            "test -e /run/secrets/vars/my_shared_generator/no_deploy_secret",
            check=False,
        )
        assert returncode != 0
        qga_m1.exec_cmd("poweroff")
        qga_m2.exec_cmd("poweroff")
        wait_vm_down("m1_machine", vm_m1)
        wait_vm_down("m2_machine", vm_m2)
    vm_m1.join()
    vm_m2.join()
