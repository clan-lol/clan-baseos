import os
import sys

import clan_cli
import pytest
import pytest_subprocess.fake_process
from clan_cli.ssh import cli
from pytest_subprocess import utils
from stdout import CaptureOutput


def test_no_args(
    monkeypatch: pytest.MonkeyPatch,
    capture_output: CaptureOutput,
) -> None:
    monkeypatch.setattr(sys, "argv", ["", "ssh"])
    with capture_output as output, pytest.raises(SystemExit):
        clan_cli.main()
    assert output.err.startswith("usage:")


# using fp fixture from pytest-subprocess
def test_ssh_no_pass(
    fp: pytest_subprocess.fake_process.FakeProcess, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = "somehost"
    user = "user"
    if os.environ.get("IN_NIX_SANDBOX"):
        monkeypatch.delenv("IN_NIX_SANDBOX")
    cmd: list[str | utils.Any] = [
        "nix",
        fp.any(),
        "shell",
        fp.any(),
        "-c",
        "ssh",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "StrictHostKeyChecking=no",
        f"{user}@{host}",
        fp.any(),
    ]
    fp.register(cmd)
    cli.ssh(
        host=host,
        user=user,
    )
    assert fp.call_count(cmd) == 1


def test_ssh_with_pass(
    fp: pytest_subprocess.fake_process.FakeProcess, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = "somehost"
    user = "user"
    if os.environ.get("IN_NIX_SANDBOX"):
        monkeypatch.delenv("IN_NIX_SANDBOX")
    cmd: list[str | utils.Any] = [
        "nix",
        fp.any(),
        "shell",
        fp.any(),
        "-c",
        "sshpass",
        "-p",
        fp.any(),
    ]
    fp.register(cmd)
    cli.ssh(
        host=host,
        user=user,
        password="XXX",
    )
    assert fp.call_count(cmd) == 1


def test_ssh_no_pass_with_torify(
    fp: pytest_subprocess.fake_process.FakeProcess, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = "somehost"
    user = "user"
    if os.environ.get("IN_NIX_SANDBOX"):
        monkeypatch.delenv("IN_NIX_SANDBOX")
    cmd: list[str | utils.Any] = [
        "nix",
        fp.any(),
        "shell",
        fp.any(),
        "-c",
        "torify",
        "ssh",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "StrictHostKeyChecking=no",
        f"{user}@{host}",
        fp.any(),
    ]
    fp.register(cmd)
    cli.ssh(
        host=host,
        user=user,
        torify=True,
    )
    assert fp.call_count(cmd) == 1


def test_ssh_with_pass_with_torify(
    fp: pytest_subprocess.fake_process.FakeProcess, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = "somehost"
    user = "user"
    if os.environ.get("IN_NIX_SANDBOX"):
        monkeypatch.delenv("IN_NIX_SANDBOX")
    cmd: list[str | utils.Any] = [
        "nix",
        fp.any(),
        "shell",
        fp.any(),
        "-c",
        "torify",
        "sshpass",
        "-p",
        fp.any(),
    ]
    fp.register(cmd)
    cli.ssh(
        host=host,
        user=user,
        password="XXX",
        torify=True,
    )
    assert fp.call_count(cmd) == 1


def test_qrcode_scan(fp: pytest_subprocess.fake_process.FakeProcess) -> None:
    cmd: list[str | utils.Any] = [fp.any()]
    fp.register(cmd, stdout="https://test.test")
    result = cli.qrcode_scan("test.png")
    assert result == "https://test.test"
