import base64
import json
import socket
from time import sleep

from clan_cli.errors import ClanError


# qga is almost like qmp, but not quite, because:
#   - server doesn't send initial message
#   - no need to initialize by asking for capabilities
#   - results need to be base64 decoded
class QgaSession:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock

    def get_response(self) -> dict:
        result = self.sock.recv(9999999)
        return json.loads(result)

    # only execute, don't wait for response
    def exec_cmd(self, cmd: str) -> None:
        self.sock.send(
            json.dumps(
                {
                    "execute": "guest-exec",
                    "arguments": {
                        "path": "/bin/sh",
                        "arg": ["-l", "-c", cmd],
                        "capture-output": True,
                    },
                }
            ).encode("utf-8")
        )

    # run, wait for result, return exitcode and output
    def run(self, cmd: str, check: bool = False) -> tuple[int, str, str]:
        self.exec_cmd(cmd)
        result_pid = self.get_response()
        pid = result_pid["return"]["pid"]
        # loop until exited=true
        status_payload = json.dumps(
            {
                "execute": "guest-exec-status",
                "arguments": {
                    "pid": pid,
                },
            }
        ).encode("utf-8")
        while True:
            self.sock.send(status_payload)
            result = self.get_response()
            if "error" in result and result["error"]["desc"].startswith("PID"):
                msg = "PID could not be found"
                raise ClanError(msg)
            if result["return"]["exited"]:
                break
            sleep(0.1)

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
