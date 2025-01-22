import contextlib
import random
import string
from configparser import ConfigParser, DuplicateSectionError, NoOptionError
from pathlib import Path


def moonlight_config_dir() -> Path:
    return Path.home() / ".config" / "Moonlight Game Streaming Project"


def moonlight_state_file() -> Path:
    return moonlight_config_dir() / "Moonlight.conf"


def load_state() -> ConfigParser | None:
    try:
        with moonlight_state_file().open() as file:
            config = ConfigParser()
            config.read_file(file)
            print(config.sections())
            return config
    except FileNotFoundError:
        print("Sunshine state file not found.")
        return None


# prepare the string for the config file
# this is how qt handles byte arrays
def convert_string_to_bytearray(data: str) -> str:
    byte_array = '"@ByteArray('
    byte_array += data.replace("\n", "\\n")
    byte_array += ')"'
    return byte_array


def convert_bytearray_to_string(byte_array: str) -> str:
    if byte_array.startswith('"@ByteArray(') and byte_array.endswith(')"'):
        byte_array = byte_array[12:-2]
        return byte_array.replace("\\n", "\n")
    return byte_array


# this must be created before moonlight is first run
def init_state(certificate: str, key: str) -> None:
    print("Initializing moonlight state.")
    moonlight_config_dir().mkdir(parents=True, exist_ok=True)
    print("Initialized moonlight config directory.")

    print("Writing moonlight state file.")
    # write the initial bootstrap config file
    with moonlight_state_file().open("w") as file:
        config = ConfigParser()
        # bytearray objects are not supported by ConfigParser,
        # so we need to adjust them ourselves
        config.add_section("General")
        config.set("General", "certificate", convert_string_to_bytearray(certificate))
        config.set("General", "key", convert_string_to_bytearray(key))
        config.set("General", "latestsupportedversion-v1", "99.99.99.99")
        config.add_section("gcmapping")
        config.set("gcmapping", "size", "0")

        config.write(file)


def write_state(data: ConfigParser) -> None:
    with moonlight_state_file().open("w") as file:
        data.write(file)


def add_sunshine_host_to_parser(
    config: ConfigParser, hostname: str, manual_host: str, certificate: str, uuid: str
) -> bool:
    with contextlib.suppress(DuplicateSectionError):
        config.add_section("hosts")

    # amount of hosts
    try:
        no_hosts = int(config.get("hosts", "size"))
    except NoOptionError:
        no_hosts = 0

    new_host = no_hosts + 1

    config.set(
        "hosts", f"{new_host}\\srvcert", convert_string_to_bytearray(certificate)
    )
    config.set("hosts", "size", str(new_host))
    config.set("hosts", f"{new_host}\\uuid", uuid)
    config.set("hosts", f"{new_host}\\hostname", hostname)
    config.set("hosts", f"{new_host}\\nvidiasv", "false")
    config.set("hosts", f"{new_host}\\customname", "false")
    config.set("hosts", f"{new_host}\\manualaddress", manual_host)
    config.set("hosts", f"{new_host}\\manualport", "47989")
    config.set("hosts", f"{new_host}\\remoteport", "0")
    config.set("hosts", f"{new_host}\\remoteaddress", "")
    config.set("hosts", f"{new_host}\\localaddress", "")
    config.set("hosts", f"{new_host}\\localport", "0")
    config.set("hosts", f"{new_host}\\ipv6port", "0")
    config.set("hosts", f"{new_host}\\ipv6address", "")
    config.set(
        "hosts", f"{new_host}\\mac", convert_string_to_bytearray("\\xceop\\x8d\\xfc{")
    )
    add_app(config, "Desktop", new_host, 1, 881448767)
    add_app(config, "Low Res Desktop", new_host, 2, 303580669)
    add_app(config, "Steam Big Picture", new_host, 3, 1093255277)

    print(config.items("hosts"))
    return True


# set default apps for the host for now
# TODO: do this dynamically
def add_app(
    config: ConfigParser, name: str, host_id: int, app_id: int, app_no: int
) -> None:
    identifier = f"{host_id}\\apps\\{app_id}\\"
    config.set("hosts", f"{identifier}appcollector", "false")
    config.set("hosts", f"{identifier}directlaunch", "false")
    config.set("hosts", f"{identifier}hdr", "false")
    config.set("hosts", f"{identifier}hidden", "false")
    config.set("hosts", f"{identifier}id", f"{app_no}")
    config.set("hosts", f"{identifier}name", f"{name}")


def get_moonlight_certificate() -> str:
    config = load_state()
    if config is None:
        msg = "Moonlight state file not found."
        raise FileNotFoundError(msg)
    certificate = config.get("General", "certificate")
    certificate = convert_bytearray_to_string(certificate)
    return certificate


def gen_pin() -> str:
    return "".join(random.choice(string.digits) for _ in range(4))


def add_sunshine_host(
    hostname: str, manual_host: str, certificate: str, uuid: str
) -> bool:
    config = load_state()
    if config is None:
        return False
    hostname = "test"
    add_sunshine_host_to_parser(config, hostname, manual_host, certificate, uuid)
    write_state(config)
    return True
