import functools
from collections.abc import Callable
from pathlib import Path

from .groups import get_groups


def get_secrets_filter_for_users_or_machines(
    what: str,
    flake_dir: Path,
    name: str,
) -> Callable[[Path], bool]:
    groups_names = get_groups(flake_dir, what, name)

    def filter_secrets(secret: Path) -> bool:
        if (secret / what / name).is_symlink():
            return True
        groups_folder = secret / "groups"
        return any((groups_folder / name).is_symlink() for name in groups_names)

    return filter_secrets


get_secrets_filter_for_user = functools.partial(
    get_secrets_filter_for_users_or_machines,
    "users",
)


get_secrets_filter_for_machine = functools.partial(
    get_secrets_filter_for_users_or_machines,
    "machines",
)
