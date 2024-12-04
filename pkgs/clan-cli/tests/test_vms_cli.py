from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from clan_cli.clan_uri import FlakeId
from clan_cli.machines.machines import Machine
from clan_cli.vms.run import inspect_vm, spawn_vm
from fixtures_flakes import ClanFlake, FlakeForTest
from helpers import cli
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
    cli.run(["vms", "run", "--no-block", "vm1", "-c", "shutdown", "-h", "now"])


@pytest.mark.skipif(no_kvm, reason="Requires KVM")
@pytest.mark.impure
def test_vm_persistence(
    flake: ClanFlake,
) -> None:
    # set up a clan flake with some systemd services to test persistence
    config = flake.machines["my_machine"]
    config["nixpkgs"]["hostPlatform"] = "x86_64-linux"
    # logrotate-checkconf doesn't work in VM because /nix/store is owned by nobody
    config["systemd"]["services"]["logrotate-checkconf"]["enable"] = False
    config["services"]["getty"]["autologinUser"] = "root"
    config["clan"]["virtualisation"] = {"graphics": False}
    config["clan"]["core"]["networking"] = {"targetHost": "client"}
    config["clan"]["core"]["state"]["my_state"]["folders"] = [
        # to be owned by root
        "/var/my-state",
        # to be owned by user 'test'
        "/var/user-state",
    ]
    config["users"]["users"] = {
        "test": {"initialPassword": "test", "isSystemUser": True, "group": "users"},
        "root": {"initialPassword": "root"},
    }

    flake.refresh()

    vm_config = inspect_vm(machine=Machine("my_machine", FlakeId(str(flake.path))))

    with spawn_vm(vm_config) as vm, vm.qga_connect() as qga:
        # create state via qmp command instead of systemd service
        qga.run(["/bin/sh", "-c", "echo 'dream2nix' > /var/my-state/root"])
        qga.run(["/bin/sh", "-c", "echo 'dream2nix' > /var/my-state/test"])
        qga.run(["/bin/sh", "-c", "chown test /var/my-state/test"])
        qga.run(["/bin/sh", "-c", "chown test /var/user-state"])
        qga.run_nonblocking(["shutdown", "-h", "now"])

    ## start vm again
    with spawn_vm(vm_config) as vm, vm.qga_connect() as qga:
        # check state exists
        qga.run(["cat", "/var/my-state/test"])
        # ensure root file is owned by root
        qga.run(["stat", "-c", "%U", "/var/my-state/root"])
        # ensure test file is owned by test
        qga.run(["stat", "-c", "%U", "/var/my-state/test"])
        # ensure /var/user-state is owned by test
        qga.run(["stat", "-c", "%U", "/var/user-state"])

        # ensure that the file created by the service is still there and has the expected content
        result = qga.run(["cat", "/var/my-state/test"])
        assert result.stdout == "dream2nix\n", result.stdout

        # check for errors
        result = qga.run(["cat", "/var/my-state/error"], check=False)
        assert result.returncode == 1, result.stdout

        # check all systemd services are OK, or print details
        result = qga.run(
            [
                "/bin/sh",
                "-c",
                "systemctl --failed | tee /tmp/log | grep -q '0 loaded units listed' || ( cat /tmp/log && false )",
            ],
        )
