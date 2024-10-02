from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from clan_cli.clan_uri import FlakeId
from clan_cli.machines.machines import Machine
from clan_cli.vms.run import inspect_vm, spawn_vm
from fixtures_flakes import FlakeForTest, generate_flake
from helpers import cli
from helpers.nixos_config import nested_dict
from root import CLAN_CORE
from stdout import CaptureOutput

if TYPE_CHECKING:
    from age_keys import KeyPair

no_kvm = not Path("/dev/kvm").exists()


@pytest.mark.impure
def test_inspect(
    test_flake_with_core: FlakeForTest, capture_output: CaptureOutput
) -> None:
    with capture_output as output:
        cli.run(["vms", "inspect", "--flake", str(test_flake_with_core.path), "vm1"])
    assert "Cores" in output.out


@pytest.mark.skipif(no_kvm, reason="Requires KVM")
@pytest.mark.impure
def test_run(
    monkeypatch: pytest.MonkeyPatch,
    test_flake_with_core: FlakeForTest,
    age_keys: list["KeyPair"],
) -> None:
    monkeypatch.chdir(test_flake_with_core.path)
    monkeypatch.setenv("SOPS_AGE_KEY", age_keys[0].privkey)
    cli.run(
        [
            "secrets",
            "users",
            "add",
            "user1",
            age_keys[0].pubkey,
        ]
    )
    cli.run(
        [
            "secrets",
            "groups",
            "add-user",
            "admins",
            "user1",
        ]
    )
    cli.run(["vms", "run", "vm1"])


@pytest.mark.skipif(no_kvm, reason="Requires KVM")
@pytest.mark.impure
def test_vm_persistence(
    monkeypatch: pytest.MonkeyPatch,
    temporary_home: Path,
) -> None:
    # set up a clan flake with some systemd services to test persistence
    config = nested_dict()
    # logrotate-checkconf doesn't work in VM because /nix/store is owned by nobody
    config["my_machine"]["systemd"]["services"]["logrotate-checkconf"]["enable"] = False
    config["my_machine"]["services"]["getty"]["autologinUser"] = "root"
    config["my_machine"]["clan"]["virtualisation"] = {"graphics": False}
    config["my_machine"]["clan"]["networking"] = {"targetHost": "client"}
    config["my_machine"]["clan"]["core"]["state"]["my_state"]["folders"] = [
        # to be owned by root
        "/var/my-state",
        # to be owned by user 'test'
        "/var/user-state",
    ]
    config["my_machine"]["users"]["users"] = {
        "test": {"initialPassword": "test", "isSystemUser": True, "group": "users"},
        "root": {"initialPassword": "root"},
    }

    flake = generate_flake(
        temporary_home,
        flake_template=CLAN_CORE / "templates" / "minimal",
        machine_configs=config,
    )

    vm_config = inspect_vm(machine=Machine("my_machine", FlakeId(str(flake.path))))

    with spawn_vm(vm_config) as vm, vm.qga_connect() as qga:
        # create state via qmp command instead of systemd service
        qga.run("echo 'dream2nix' > /var/my-state/root", check=True)
        qga.run("echo 'dream2nix' > /var/my-state/test", check=True)
        qga.run("chown test /var/my-state/test", check=True)
        qga.run("chown test /var/user-state", check=True)
        qga.run("touch /var/my-state/rebooting", check=True)

    ## start vm again
    with spawn_vm(vm_config) as vm, vm.qga_connect() as qga:
        # check state exists
        qga.run("cat /var/my-state/test", check=True)
        # ensure root file is owned by root
        qga.run("stat -c '%U' /var/my-state/root", check=True)
        # ensure test file is owned by test
        qga.run("stat -c '%U' /var/my-state/test", check=True)
        # ensure /var/user-state is owned by test
        qga.run("stat -c '%U' /var/user-state", check=True)

        # ensure that the file created by the service is still there and has the expected content
        exitcode, out, err = qga.run("cat /var/my-state/test")
        assert exitcode == 0, err
        assert out == "dream2nix\n", out

        # check for errors
        exitcode, out, err = qga.run("cat /var/my-state/error")
        assert exitcode == 1, out

        # check all systemd services are OK, or print details
        exitcode, out, err = qga.run(
            "systemctl --failed | tee /tmp/yolo | grep -q '0 loaded units listed' || ( cat /tmp/yolo && false )"
        )
        assert exitcode == 0, out
