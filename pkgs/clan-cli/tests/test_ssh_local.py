from clan_cli.cmd import Log, RunOpts
from clan_cli.ssh.host import Host
from clan_cli.ssh.host_group import HostGroup

hosts = HostGroup([Host("some_host")])


def test_run_environment() -> None:
    p2 = hosts.run_local(
        ["echo $env_var"], extra_env={"env_var": "true"}, shell=True, log=Log.STDERR
    )
    assert p2[0].result.stdout == "true\n"

    p3 = hosts.run_local(["env"], extra_env={"env_var": "true"}, log=Log.STDERR)
    assert "env_var=true" in p3[0].result.stdout


def test_run_local() -> None:
    hosts.run_local(["echo", "hello"])


def test_timeout() -> None:
    try:
        hosts.run_local(["sleep", "10"], timeout=0.01)
    except Exception:
        pass
    else:
        msg = "should have raised TimeoutExpired"
        raise AssertionError(msg)


def test_run_function() -> None:
    def some_func(h: Host) -> bool:
        par = h.run_local(["echo", "hello"], RunOpts(log=Log.STDERR))
        return par.stdout == "hello\n"

    res = hosts.run_function(some_func)
    assert res[0].result


def test_run_exception() -> None:
    try:
        hosts.run_local(["exit 1"], shell=True)
    except Exception:
        pass
    else:
        msg = "should have raised Exception"
        raise AssertionError(msg)


def test_run_function_exception() -> None:
    def some_func(h: Host) -> None:
        h.run_local(["exit 1"], RunOpts(shell=True))

    try:
        hosts.run_function(some_func)
    except Exception:
        pass
    else:
        msg = "should have raised Exception"
        raise AssertionError(msg)


def test_run_local_non_shell() -> None:
    p2 = hosts.run_local(["echo", "1"], log=Log.STDERR)
    assert p2[0].result.stdout == "1\n"
