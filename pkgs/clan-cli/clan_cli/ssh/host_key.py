# Adapted from https://github.com/numtide/deploykit

from enum import Enum

from clan_cli.errors import ClanError


class HostKeyCheck(Enum):
    # Strictly check ssh host keys, prompt for unknown ones
    STRICT = 0
    # Ask for confirmation on first use
    ASK = 1
    # Trust on ssh keys on first use
    TOFU = 2
    # Do not check ssh host keys
    NONE = 3

    @staticmethod
    def from_str(label: str) -> "HostKeyCheck":
        if label.upper() in HostKeyCheck.__members__:
            return HostKeyCheck[label.upper()]
        msg = f"Invalid choice: {label}."
        description = "Choose from: " + ", ".join(HostKeyCheck.__members__)
        raise ClanError(msg, description=description)

    def __str__(self) -> str:
        return self.name.lower()

    def to_ssh_opt(self) -> list[str]:
        match self:
            case HostKeyCheck.STRICT:
                return ["-o", "StrictHostKeyChecking=yes"]
            case HostKeyCheck.ASK:
                return []
            case HostKeyCheck.TOFU:
                return ["-o", "StrictHostKeyChecking=accept-new"]
            case HostKeyCheck.NONE:
                return [
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                ]
            case _:
                msg = "Invalid HostKeyCheck"
                raise ClanError(msg)
