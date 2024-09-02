import json
from typing import TYPE_CHECKING

import pytest
from clan_cli.api.modules import list_modules
from clan_cli.clan_uri import FlakeId
from clan_cli.inventory import (
    Machine,
    MachineDeploy,
    ServiceBorgbackup,
    ServiceBorgbackupRole,
    ServiceBorgbackupRoleClient,
    ServiceBorgbackupRoleServer,
    ServiceMeta,
    load_inventory_json,
    save_inventory,
)
from clan_cli.machines.create import create_machine
from clan_cli.nix import nix_eval, run_no_stdout
from fixtures_flakes import FlakeForTest

if TYPE_CHECKING:
    from age_keys import KeyPair

from clan_cli.machines.facts import machine_get_fact
from helpers import cli


@pytest.mark.with_core
def test_list_modules(test_flake_with_core: FlakeForTest) -> None:
    base_path = test_flake_with_core.path
    modules_info = list_modules(base_path)

    assert len(modules_info.items()) > 1
    # Random test for those two modules
    assert "borgbackup" in modules_info
    assert "syncthing" in modules_info


@pytest.mark.impure
def test_add_module_to_inventory(
    monkeypatch: pytest.MonkeyPatch,
    test_flake_with_core: FlakeForTest,
    age_keys: list["KeyPair"],
) -> None:
    base_path = test_flake_with_core.path
    monkeypatch.chdir(test_flake_with_core.path)
    monkeypatch.setenv("SOPS_AGE_KEY", age_keys[0].privkey)

    cli.run(
        [
            "secrets",
            "users",
            "add",
            "--flake",
            str(test_flake_with_core.path),
            "user1",
            age_keys[0].pubkey,
        ]
    )
    create_machine(
        FlakeId(str(base_path)),
        Machine(
            name="machine1", tags=[], system="x86_64-linux", deploy=MachineDeploy()
        ),
    )

    inventory = load_inventory_json(base_path)

    inventory.services.borgbackup = {
        "borg1": ServiceBorgbackup(
            meta=ServiceMeta(name="borg1"),
            roles=ServiceBorgbackupRole(
                client=ServiceBorgbackupRoleClient(
                    machines=["machine1"],
                ),
                server=ServiceBorgbackupRoleServer(
                    machines=["machine1"],
                ),
            ),
        )
    }

    save_inventory(inventory, base_path, "Add borgbackup service")

    cmd = ["facts", "generate", "--flake", str(test_flake_with_core.path), "machine1"]
    cli.run(cmd)

    ssh_key = machine_get_fact(base_path, "machine1", "borgbackup.ssh.pub")

    cmd = nix_eval(
        [
            f"{base_path}#nixosConfigurations.machine1.config.services.borgbackup.repos",
            "--json",
        ]
    )
    proc = run_no_stdout(cmd)
    res = json.loads(proc.stdout.strip())

    assert res["machine1"]["authorizedKeys"] == [ssh_key]
