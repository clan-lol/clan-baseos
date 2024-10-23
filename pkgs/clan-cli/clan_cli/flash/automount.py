import logging
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from clan_cli.cmd import Log, run
from clan_cli.errors import ClanError

log = logging.getLogger(__name__)


@contextmanager
def pause_automounting(devices: list[Path]) -> Generator[None, None, None]:
    """
    Pause automounting on the device for the duration of this context
    manager
    """

    if shutil.which("udevadm") is None:
        msg = "udev is required to disable automounting"
        log.warning(msg)
        yield None
        return

    inhibit_path = Path(__file__).parent / "inhibit.sh"
    if not inhibit_path.exists():
        msg = f"{inhibit_path} not found"
        raise ClanError(msg)

    str_devs = [str(dev) for dev in devices]
    cmd = ["sudo", str(inhibit_path), "enable", *str_devs]
    result = run(cmd, log=Log.BOTH, check=False, needs_user_terminal=True)
    if result.returncode != 0:
        log.error("Failed to inhibit automounting")
    yield None
    cmd = ["sudo", str(inhibit_path), "disable", *str_devs]
    result = run(cmd, log=Log.BOTH, check=False)
    if result.returncode != 0:
        log.error("Failed to re-enable automounting")
