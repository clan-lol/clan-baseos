import configparser
import os

# address_family = both
# channels = 5
# pkey = /var/lib/sunshine/sunshine.key
# cert = /var/lib/sunshine/sunshine.cert
# file_state = /var/lib/sunshine/state.json
# credentials_file = /var/lib/sunshine/credentials.json

PSEUDO_SECTION = "DEFAULT"


class Config:
    _instance = None

    def __new__(cls, config_location: str | None = None) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = configparser.ConfigParser()
            config = config_location or cls._instance.default_sunshine_config_file()
            cls._instance.config_location = config
            with open(config) as f:
                config_string = f"[{PSEUDO_SECTION}]\n" + f.read()
                print(config_string)
                cls._instance.config.read_string(config_string)
        return cls._instance

    def default_sunshine_config_dir(self) -> str:
        return os.path.join(os.path.expanduser("~"), ".config", "sunshine")

    def default_sunshine_config_file(self) -> str:
        return os.path.join(self.default_sunshine_config_dir(), "sunshine.conf")

    def get_private_key(self) -> str:
        return self.config.get(PSEUDO_SECTION, "pkey")

    def get_certificate(self) -> str:
        return self.config.get(PSEUDO_SECTION, "cert")

    def get_state_file(self) -> str:
        return self.config.get(PSEUDO_SECTION, "file_state")

    def get_credentials_file(self) -> str:
        return self.config.get(PSEUDO_SECTION, "credentials_file")
