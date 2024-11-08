from dataclasses import dataclass, fields
from typing import Any


@dataclass
class HostPlatform:
    config: str
    darwinArch: str
    darwinMinVersion: str
    darwinSdkVersion: str
    is32bit: bool
    is64bit: bool
    isx86_64: bool
    isAarch: bool
    isDarwin: bool
    isFreeBSD: bool
    isLinux: bool
    isMacOS: bool
    isWindows: bool
    isAndroid: bool
    linuxArch: str
    qemuArch: str
    system: str
    ubootArch: str

    # ruff: noqa: N815

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HostPlatform":
        """
        Factory method that creates an instance of HostPlatform from a dictionary.
        Extra fields in the dictionary are ignored.

        Args:
        data (dict): A dictionary containing values for initializing HostPlatform.

        Returns:
        HostPlatform: An instance of the HostPlatform class.
        """
        # Dynamically extract field names from the dataclass
        valid_keys = {field.name for field in fields(HostPlatform)}

        # Filter the dictionary to only include items with keys that are valid
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}

        # Pass the filtered data to the HostPlatform constructor
        return HostPlatform(**filtered_data)
