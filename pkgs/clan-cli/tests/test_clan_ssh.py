import argparse
import json
import tempfile
import pytest
import sys
from typing import Union

import pytest_subprocess.fake_process
from pytest_subprocess import utils

import clan_cli.ssh

def test_no_args(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["", "ssh"])
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        clan_cli.main()
    captured = capsys.readouterr()
    assert captured.err.startswith("usage:")


# using fp fixture from pytest-subprocess
def test_ssh_no_pass(fp: pytest_subprocess.fake_process.FakeProcess) -> None:
    host = "somehost"
    user = "user"
    cmd: list[Union[str, utils.Any]] = [
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
    clan_cli.ssh.ssh(
        host=host,
        user=user,
    )
    assert fp.call_count(cmd) == 1


def test_ssh_with_pass(fp: pytest_subprocess.fake_process.FakeProcess) -> None:
    host = "somehost"
    user = "user"
    cmd: list[Union[str, utils.Any]] = [
        "nix",
        "shell",
        "nixpkgs#sshpass",
        "-c",
        fp.any(),
    ]
    fp.register(cmd)
    clan_cli.ssh.ssh(
        host=host,
        user=user,
        password="XXX",
    )
    assert fp.call_count(cmd) == 1
