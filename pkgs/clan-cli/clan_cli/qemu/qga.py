import base64
import time
import types

from clan_cli.errors import ClanError
from clan_cli.qemu.qmp import QEMUMonitorProtocol


# qga is almost like qmp, but not quite, because:
#   - server doesn't send initial message
#   - no need to initialize by asking for capabilities
#   - results need to be base64 decoded
class QgaSession:
    def __init__(self, address: str) -> None:
        self.client = QEMUMonitorProtocol(address)
        self.client.connect(negotiate=False)

    def __enter__(self) -> "QgaSession":
        # Implement context manager enter function.
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        # Implement context manager exit function.
        self.client.close()

    def run_nonblocking(self, cmd: list[str]) -> int:
        result_pid = self.client.cmd(
            "guest-exec", {"path": cmd[0], "arg": cmd[1:], "capture-output": True}
        )
        if result_pid is None:
            msg = "Could not get PID from QGA"
            raise ClanError(msg)
        return result_pid["return"]["pid"]

    # run, wait for result, return exitcode and output
    def run(self, cmd: list[str], check: bool = False) -> tuple[int, str, str]:
        pid = self.run_nonblocking(cmd)
        # loop until exited=true
        while True:
            result = self.client.cmd("guest-exec-status", {"pid": pid})
            if result is None:
                msg = "Could not get status from QGA"
                raise ClanError(msg)
            if "error" in result and result["error"]["desc"].startswith("PID"):
                msg = "PID could not be found"
                raise ClanError(msg)
            if result["return"]["exited"]:
                break
            time.sleep(0.1)

        exitcode = result["return"]["exitcode"]
        stdout = (
            ""
            if "out-data" not in result["return"]
            else base64.b64decode(result["return"]["out-data"]).decode("utf-8")
        )
        stderr = (
            ""
            if "err-data" not in result["return"]
            else base64.b64decode(result["return"]["err-data"]).decode("utf-8")
        )
        if check and exitcode != 0:
            msg = f"Command on guest failed\nCommand: {cmd}\nExitcode {exitcode}\nStdout: {stdout}\nStderr: {stderr}"
            raise ClanError(msg)
        return exitcode, stdout, stderr
