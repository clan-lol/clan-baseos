from dataclasses import dataclass
from pathlib import Path

from clan_cli.clan_uri import FlakeId
from clan_cli.errors import ClanError
from clan_cli.facts.generate import generate_facts
from clan_cli.inventory import (
    IwdConfig,
    IwdConfigNetwork,
    ServiceIwd,
    ServiceIwdRole,
    ServiceIwdRoleDefault,
    ServiceMeta,
    load_inventory_eval,
    save_inventory,
)
from clan_cli.machines.machines import Machine
from clan_cli.secrets.sops import (
    maybe_get_public_key,
    maybe_get_user_or_machine,
)

from . import API


def instance_name(machine_name: str) -> str:
    return f"{machine_name}_wifi_0_"


@API.register
def get_iwd_service(base_url: str, machine_name: str) -> ServiceIwd:
    """
    Return the admin service of a clan.

    There is only one admin service. This might be changed in the future
    """
    inventory = load_inventory_eval(base_url)
    service_config = inventory.services.iwd.get(instance_name(machine_name))
    if service_config:
        return service_config

    # Empty service
    return ServiceIwd(
        meta=ServiceMeta(name="wifi_0"),
        roles=ServiceIwdRole(default=ServiceIwdRoleDefault(machines=[machine_name])),
        config=IwdConfig(networks={}),
    )


@dataclass
class NetworkConfig:
    ssid: str
    password: str


@API.register
def set_iwd_service_for_machine(
    base_url: str, machine_name: str, networks: dict[str, NetworkConfig]
) -> None:
    """
    Set the admin service of a clan
    Every machine is by default part of the admin service via the 'all' tag
    """
    _instance_name = instance_name(machine_name)

    inventory = load_inventory_eval(base_url)

    instance = ServiceIwd(
        meta=ServiceMeta(name="wifi_0"),
        roles=ServiceIwdRole(
            default=ServiceIwdRoleDefault(
                machines=[machine_name],
            )
        ),
        config=IwdConfig(
            networks={k: IwdConfigNetwork(v.ssid) for k, v in networks.items()}
        ),
    )

    inventory.services.iwd[_instance_name] = instance

    save_inventory(
        inventory,
        base_url,
        f"Set iwd service: '{_instance_name}'",
    )

    pubkey = maybe_get_public_key()
    if not pubkey:
        # TODO: do this automatically
        # pubkey = generate_key()
        raise ClanError(msg="No public key found. Please initialize your key.")

    registered_key = maybe_get_user_or_machine(Path(base_url), pubkey)
    if not registered_key:
        # TODO: do this automatically
        # username = os.getlogin()
        # add_user(Path(base_url), username, pubkey, force=False)
        raise ClanError(msg="Your public key is not registered for use with this clan.")

    password_dict = {f"iwd.{net.ssid}": net.password for net in networks.values()}
    for net in networks.values():
        generate_facts(
            service=f"iwd.{net.ssid}",
            machines=[Machine(machine_name, FlakeId(base_url))],
            regenerate=True,
            # Just returns the password
            prompt=lambda service, _msg: password_dict[service],
        )
