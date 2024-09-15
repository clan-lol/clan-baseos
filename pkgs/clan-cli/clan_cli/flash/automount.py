import logging
import os
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from clan_cli.cmd import run
from clan_cli.errors import ClanError

log = logging.getLogger(__name__)


@contextmanager
def pause_automounting(
    devices: list[Path], no_udev: bool
) -> Generator[None, None, None]:
    """
    Pause automounting on the device for the duration of this context
    manager
    """
    if no_udev:
        yield None
        return

    if shutil.which("udevadm") is None:
        msg = "udev is required to disable automounting"
        log.warning(msg)
        yield None
        return

    if os.geteuid() != 0:
        msg = "root privileges are required to disable automounting"
        raise ClanError(msg)
    try:
        # See /usr/lib/udisks2/udisks2-inhibit
        rules_dir = Path("/run/udev/rules.d")
        rules_dir.mkdir(exist_ok=True)
        rule_files: list[Path] = []
        for device in devices:
            devpath: str = str(device)
            rule_file: Path = (
                rules_dir / f"90-udisks-inhibit-{devpath.replace('/', '_')}.rules"
            )
            with rule_file.open("w") as fd:
                print(
                    'SUBSYSTEM=="block", ENV{DEVNAME}=="'
                    + devpath
                    + '*", ENV{UDISKS_IGNORE}="1"',
                    file=fd,
                )
                fd.flush()
                os.fsync(fd.fileno())
            rule_files.append(rule_file)
        run(["udevadm", "control", "--reload"])
        run(["udevadm", "trigger", "--settle", "--subsystem-match=block"])

        yield None
    except Exception as ex:
        log.fatal(ex)
    finally:
        for rule_file in rule_files:
            rule_file.unlink(missing_ok=True)
        run(["udevadm", "control", "--reload"], check=False)
        run(["udevadm", "trigger", "--settle", "--subsystem-match=block"], check=False)
