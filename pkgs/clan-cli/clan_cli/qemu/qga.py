import base64
import time
import types
from dataclasses import dataclass

from clan_cli.errors import ClanError
from clan_cli.qemu.qmp import QEMUMonitorProtocol


@dataclass
class VmCommandResult:
    returncode: int
    stdout: str | None
    stderr: str | None


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
        try:
            return result_pid["return"]["pid"]
        except KeyError as e:
            if "error" in result_pid:
                msg = f"Could not run command: {result_pid['error']['desc']}"
                raise ClanError(msg) from e
            msg = f"PID could not be found: {result_pid}"
            raise ClanError(msg) from e

    # run, wait for result, return exitcode and output
    def run(self, cmd: list[str], check: bool = True) -> VmCommandResult:
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
        err_data = result["return"].get("err-data")
        stdout = None
        stderr = None
        if out_data := result["return"].get("out-data"):
            stdout = base64.b64decode(out_data).decode("utf-8")
        if err_data is not None:
            stderr = base64.b64decode(err_data).decode("utf-8")
        if check and exitcode != 0:
            msg = f"Command on guest failed\nCommand: {cmd}\nExitcode {exitcode}\nStdout: {stdout}\nStderr: {stderr}"
            raise ClanError(msg)
        return VmCommandResult(exitcode, stdout, stderr)
