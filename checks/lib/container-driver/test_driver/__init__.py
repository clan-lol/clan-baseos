import argparse
import os
import re
import subprocess
import time
import types
from collections.abc import Callable
from contextlib import _GeneratorContextManager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .logger import AbstractLogger, CompositeLogger, TerminalLogger


class Error(Exception):
    pass


def prepare_machine_root(machinename: str, root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("etc").mkdir(parents=True, exist_ok=True)
    root.joinpath(".env").write_text(
        "\n".join(f"{k}={v}" for k, v in os.environ.items())
    )


def pythonize_name(name: str) -> str:
    return re.sub(r"^[^A-z_]|[^A-z0-9_]", "_", name)


def retry(fn: Callable, timeout: int = 900) -> None:
    """Call the given function repeatedly, with 1 second intervals,
    until it returns True or a timeout is reached.
    """

    for _ in range(timeout):
        if fn(False):
            return
        time.sleep(1)

    if not fn(True):
        msg = f"action timed out after {timeout} seconds"
        raise Error(msg)


class Machine:
    def __init__(
        self,
        name: str,
        toplevel: Path,
        logger: AbstractLogger,
        rootdir: Path,
        out_dir: str,
    ) -> None:
        self.name = name
        self.toplevel = toplevel
        self.out_dir = out_dir
        self.process: subprocess.Popen | None = None
        self.rootdir: Path = rootdir
        self.logger = logger

    def start(self) -> None:
        prepare_machine_root(self.name, self.rootdir)
        cmd = [
            "systemd-nspawn",
            "--keep-unit",
            "-M",
            self.name,
            "-D",
            self.rootdir,
            "--register=no",
            "--resolv-conf=off",
            "--bind-ro=/nix/store",
            "--bind",
            self.out_dir,
            "--bind=/proc:/run/host/proc",
            "--bind=/sys:/run/host/sys",
            "--private-network",
            self.toplevel.joinpath("init"),
        ]
        env = os.environ.copy()
        env["SYSTEMD_NSPAWN_UNIFIED_HIERARCHY"] = "1"
        self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, env=env)
        self.container_pid = self.get_systemd_process()

    def get_systemd_process(self) -> int:
        assert self.process is not None, "Machine not started"
        assert self.process.stdout is not None, "Machine has no stdout"
        for line in self.process.stdout:
            print(line, end="")
            if (
                line.startswith("systemd[1]: Startup finished in")
                or "Welcome to NixOS" in line
            ):
                break
        else:
            msg = f"Failed to start container {self.name}"
            raise RuntimeError(msg)
        childs = (
            Path(f"/proc/{self.process.pid}/task/{self.process.pid}/children")
            .read_text()
            .split()
        )
        assert (
            len(childs) == 1
        ), f"Expected exactly one child process for systemd-nspawn, got {childs}"
        try:
            return int(childs[0])
        except ValueError as e:
            msg = f"Failed to parse child process id {childs[0]}"
            raise RuntimeError(msg) from e

    def get_unit_info(self, unit: str) -> dict[str, str]:
        proc = self.systemctl(f'--no-pager show "{unit}"')
        if proc.returncode != 0:
            msg = (
                f'retrieving systemctl info for unit "{unit}"'
                f" failed with exit code {proc.returncode}"
            )
            raise Error(msg)

        line_pattern = re.compile(r"^([^=]+)=(.*)$")

        def tuple_from_line(line: str) -> tuple[str, str]:
            match = line_pattern.match(line)
            assert match is not None
            return match[1], match[2]

        return dict(
            tuple_from_line(line)
            for line in proc.stdout.split("\n")
            if line_pattern.match(line)
        )

    def execute(
        self,
        command: str,
        check_return: bool = True,
        check_output: bool = True,
        timeout: int | None = 900,
    ) -> subprocess.CompletedProcess:
        """
        Execute a shell command, returning a list `(status, stdout)`.

        Commands are run with `set -euo pipefail` set:

        -   If several commands are separated by `;` and one fails, the
            command as a whole will fail.

        -   For pipelines, the last non-zero exit status will be returned
            (if there is one; otherwise zero will be returned).

        -   Dereferencing unset variables fails the command.

        -   It will wait for stdout to be closed.

        If the command detaches, it must close stdout, as `execute` will wait
        for this to consume all output reliably. This can be achieved by
        redirecting stdout to stderr `>&2`, to `/dev/console`, `/dev/null` or
        a file. Examples of detaching commands are `sleep 365d &`, where the
        shell forks a new process that can write to stdout and `xclip -i`, where
        the `xclip` command itself forks without closing stdout.

        Takes an optional parameter `check_return` that defaults to `True`.
        Setting this parameter to `False` will not check for the return code
        and return -1 instead. This can be used for commands that shut down
        the VM and would therefore break the pipe that would be used for
        retrieving the return code.

        A timeout for the command can be specified (in seconds) using the optional
        `timeout` parameter, e.g., `execute(cmd, timeout=10)` or
        `execute(cmd, timeout=None)`. The default is 900 seconds.
        """

        # Always run command with shell opts
        command = f"set -eo pipefail; source /etc/profile; set -u; {command}"

        proc = subprocess.run(
            [
                "nsenter",
                "--target",
                str(self.container_pid),
                "--mount",
                "--uts",
                "--ipc",
                "--net",
                "--pid",
                "--cgroup",
                "/bin/sh",
                "-c",
                command,
            ],
            timeout=timeout,
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        return proc

    def nested(
        self, msg: str, attrs: dict[str, str] | None = None
    ) -> _GeneratorContextManager:
        if attrs is None:
            attrs = {}
        my_attrs = {"machine": self.name}
        my_attrs.update(attrs)
        return self.logger.nested(msg, my_attrs)

    def systemctl(self, q: str) -> subprocess.CompletedProcess:
        """
        Runs `systemctl` commands with optional support for
        `systemctl --user`

        ```py
        # run `systemctl list-jobs --no-pager`
        machine.systemctl("list-jobs --no-pager")

        # spawn a shell for `any-user` and run
        # `systemctl --user list-jobs --no-pager`
        machine.systemctl("list-jobs --no-pager", "any-user")
        ```
        """
        return self.execute(f"systemctl {q}")

    def wait_until_succeeds(self, command: str, timeout: int = 900) -> str:
        """
        Repeat a shell command with 1-second intervals until it succeeds.
        Has a default timeout of 900 seconds which can be modified, e.g.
        `wait_until_succeeds(cmd, timeout=10)`. See `execute` for details on
        command execution.
        Throws an exception on timeout.
        """
        output = ""

        def check_success(_: Any) -> bool:
            nonlocal output
            result = self.execute(command, timeout=timeout)
            return result.returncode == 0

        with self.nested(f"waiting for success: {command}"):
            retry(check_success, timeout)
            return output

    def wait_for_unit(self, unit: str, timeout: int = 900) -> None:
        """
        Wait for a systemd unit to get into "active" state.
        Throws exceptions on "failed" and "inactive" states as well as after
        timing out.
        """

        def check_active(_: bool) -> bool:
            info = self.get_unit_info(unit)
            state = info["ActiveState"]
            if state == "failed":
                proc = self.systemctl(f"--lines 0 status {unit}")
                journal = self.execute(f"journalctl -u {unit} --no-pager")
                msg = f'unit "{unit}" reached state "{state}":\n{proc.stdout}\n{journal.stdout}'
                raise Error(msg)

            if state == "inactive":
                proc = self.systemctl("list-jobs --full 2>&1")
                if "No jobs" in proc.stdout:
                    info = self.get_unit_info(unit)
                    if info["ActiveState"] == state:
                        msg = f'unit "{unit}" is inactive and there are no pending jobs'
                        raise Error(msg)

            return state == "active"

        retry(check_active, timeout)

    def succeed(self, command: str, timeout: int | None = None) -> str:
        res = self.execute(command, timeout=timeout)
        if res.returncode != 0:
            msg = f"Failed to run command {command}"
            raise RuntimeError(msg)
        return res.stdout

    def shutdown(self) -> None:
        """
        Shut down the machine, waiting for the VM to exit.
        """
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None

    def release(self) -> None:
        self.shutdown()


def setup_filesystems() -> None:
    # We don't care about cleaning up the mount points, since we're running in a nix sandbox.
    Path("/run").mkdir(parents=True, exist_ok=True)
    subprocess.run(["mount", "-t", "tmpfs", "none", "/run"], check=True)
    subprocess.run(["mount", "-t", "cgroup2", "none", "/sys/fs/cgroup"], check=True)
    Path("/etc").chmod(0o755)
    Path("/etc/os-release").touch()
    Path("/etc/machine-id").write_text("a5ea3f98dedc0278b6f3cc8c37eeaeac")


class Driver:
    logger: AbstractLogger

    def __init__(
        self,
        containers: list[Path],
        logger: AbstractLogger,
        testscript: str,
        out_dir: str,
    ) -> None:
        self.containers = containers
        self.testscript = testscript
        self.out_dir = out_dir
        self.logger = logger
        setup_filesystems()

        self.tempdir = TemporaryDirectory()
        tempdir_path = Path(self.tempdir.name)

        self.machines = []
        for container in containers:
            name_match = re.match(r".*-nixos-system-(.+)-(.+)", container.name)
            if not name_match:
                msg = f"Unable to extract hostname from {container.name}"
                raise Error(msg)
            name = name_match.group(1)
            self.machines.append(
                Machine(
                    name=name,
                    toplevel=container,
                    rootdir=tempdir_path / name,
                    out_dir=self.out_dir,
                    logger=self.logger,
                )
            )

    def start_all(self) -> None:
        for machine in self.machines:
            machine.start()

    def test_symbols(self) -> dict[str, Any]:
        general_symbols = {
            "start_all": self.start_all,
            "machines": self.machines,
            "driver": self,
            "Machine": Machine,  # for typing
        }
        machine_symbols = {pythonize_name(m.name): m for m in self.machines}
        # If there's exactly one machine, make it available under the name
        # "machine", even if it's not called that.
        if len(self.machines) == 1:
            (machine_symbols["machine"],) = self.machines
        print(
            "additionally exposed symbols:\n    "
            + ", ".join(m.name for m in self.machines)
            + ",\n    "
            + ", ".join(list(general_symbols.keys()))
        )
        return {**general_symbols, **machine_symbols}

    def test_script(self) -> None:
        """Run the test script"""
        exec(self.testscript, self.test_symbols(), None)

    def run_tests(self) -> None:
        """Run the test script (for non-interactive test runs)"""
        self.test_script()

    def __enter__(self) -> "Driver":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        for machine in self.machines:
            machine.release()


def writeable_dir(arg: str) -> Path:
    """Raises an ArgumentTypeError if the given argument isn't a writeable directory
    Note: We want to fail as early as possible if a directory isn't writeable,
    since an executed nixos-test could fail (very late) because of the test-driver
    writing in a directory without proper permissions.
    """
    path = Path(arg)
    if not path.is_dir():
        msg = f"{path} is not a directory"
        raise argparse.ArgumentTypeError(msg)
    if not os.access(path, os.W_OK):
        msg = f"{path} is not a writeable directory"
        raise argparse.ArgumentTypeError(msg)
    return path


def main() -> None:
    arg_parser = argparse.ArgumentParser(prog="nixos-test-driver")
    arg_parser.add_argument(
        "--containers",
        nargs="+",
        type=Path,
        help="container system toplevel paths",
    )
    arg_parser.add_argument(
        "--test-script",
        help="the test script to run",
        type=Path,
    )
    arg_parser.add_argument(
        "-o",
        "--output-directory",
        default=Path.cwd(),
        help="the directory to bind to /run/test-results",
        type=writeable_dir,
    )
    args = arg_parser.parse_args()
    logger = CompositeLogger([TerminalLogger()])
    with Driver(
        containers=args.containers,
        testscript=args.test_script.read_text(),
        out_dir=args.output_directory.resolve(),
        logger=logger,
    ) as driver:
        driver.run_tests()
