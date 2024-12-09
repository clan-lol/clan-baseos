import pytest
from clan_cli.async_run import AsyncRuntime
from clan_cli.cmd import ClanCmdTimeoutError, Log, RunOpts
from clan_cli.errors import ClanError, CmdOut
from clan_cli.ssh.host import Host
from clan_cli.ssh.host_key import HostKeyCheck
from clan_cli.ssh.parse import parse_deployment_address


def test_parse_ipv6() -> None:
    host = parse_deployment_address("foo", "[fe80::1%eth0]:2222", HostKeyCheck.STRICT)
    assert host.host == "fe80::1%eth0"
    assert host.port == 2222
    host = parse_deployment_address("foo", "[fe80::1%eth0]", HostKeyCheck.STRICT)
    assert host.host == "fe80::1%eth0"
    assert host.port is None

    with pytest.raises(ClanError):
        # We instruct the user to use brackets for IPv6 addresses
        host = parse_deployment_address("foo", "fe80::1%eth0", HostKeyCheck.STRICT)


def test_run(hosts: list[Host], runtime: AsyncRuntime) -> None:
    for host in hosts:
        proc = runtime.async_run(
            None, host.run_local, ["echo", "hello"], RunOpts(log=Log.STDERR)
        )
    assert proc.wait().result.stdout == "hello\n"


def test_run_environment(hosts: list[Host], runtime: AsyncRuntime) -> None:
    for host in hosts:
        proc = runtime.async_run(
            None,
            host.run_local,
            ["echo $env_var"],
            RunOpts(shell=True, log=Log.STDERR),
            extra_env={"env_var": "true"},
        )
    assert proc.wait().result.stdout == "true\n"

    for host in hosts:
        p2 = runtime.async_run(
            None,
            host.run_local,
            ["env"],
            RunOpts(log=Log.STDERR),
            extra_env={"env_var": "true"},
        )
    assert "env_var=true" in p2.wait().result.stdout


def test_run_no_shell(hosts: list[Host], runtime: AsyncRuntime) -> None:
    for host in hosts:
        proc = runtime.async_run(
            None, host.run_local, ["echo", "hello"], RunOpts(log=Log.STDERR)
        )
    assert proc.wait().result.stdout == "hello\n"


def test_run_function(hosts: list[Host], runtime: AsyncRuntime) -> None:
    def some_func(h: Host) -> bool:
        p = h.run(["echo", "hello"])
        return p.stdout == "hello\n"

    for host in hosts:
        proc = runtime.async_run(None, some_func, host)
    assert proc.wait().result


def test_timeout(hosts: list[Host], runtime: AsyncRuntime) -> None:
    for host in hosts:
        proc = runtime.async_run(
            None, host.run_local, ["sleep", "10"], RunOpts(timeout=0.01)
        )
    error = proc.wait().error
    assert isinstance(error, ClanCmdTimeoutError)


def test_run_exception(hosts: list[Host], runtime: AsyncRuntime) -> None:
    for host in hosts:
        proc = runtime.async_run(
            None, host.run_local, ["exit 1"], RunOpts(shell=True, check=False)
        )
    assert proc.wait().result.returncode == 1

    try:
        for host in hosts:
            runtime.async_run(None, host.run_local, ["exit 1"], RunOpts(shell=True))
        runtime.join_all()
        runtime.check_all()
    except Exception:
        pass
    else:
        msg = "should have raised Exception"
        raise AssertionError(msg)


def test_run_function_exception(hosts: list[Host], runtime: AsyncRuntime) -> None:
    def some_func(h: Host) -> CmdOut:
        return h.run_local(["exit 1"], RunOpts(shell=True))

    try:
        for host in hosts:
            runtime.async_run(None, some_func, host)
        runtime.join_all()
        runtime.check_all()
    except Exception:
        pass
    else:
        msg = "should have raised Exception"
        raise AssertionError(msg)
