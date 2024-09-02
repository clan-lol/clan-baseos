import subprocess

from clan_cli.ssh import Host, HostGroup

hosts = HostGroup([Host("some_host")])


def test_run_environment() -> None:
    p2 = hosts.run_local(
        "echo $env_var", extra_env={"env_var": "true"}, stdout=subprocess.PIPE
    )
    assert p2[0].result.stdout == "true\n"

    p3 = hosts.run_local(["env"], extra_env={"env_var": "true"}, stdout=subprocess.PIPE)
    assert "env_var=true" in p3[0].result.stdout


def test_run_local() -> None:
    hosts.run_local("echo hello")


def test_timeout() -> None:
    try:
        hosts.run_local("sleep 10", timeout=0.01)
    except Exception:
        pass
    else:
        msg = "should have raised TimeoutExpired"
        raise AssertionError(msg)


def test_run_function() -> None:
    def some_func(h: Host) -> bool:
        p = h.run_local("echo hello", stdout=subprocess.PIPE)
        return p.stdout == "hello\n"

    res = hosts.run_function(some_func)
    assert res[0].result


def test_run_exception() -> None:
    try:
        hosts.run_local("exit 1")
    except Exception:
        pass
    else:
        msg = "should have raised Exception"
        raise AssertionError(msg)


def test_run_function_exception() -> None:
    def some_func(h: Host) -> None:
        h.run_local("exit 1")

    try:
        hosts.run_function(some_func)
    except Exception:
        pass
    else:
        msg = "should have raised Exception"
        raise AssertionError(msg)


def test_run_local_non_shell() -> None:
    p2 = hosts.run_local(["echo", "1"], stdout=subprocess.PIPE)
    assert p2[0].result.stdout == "1\n"
