import subprocess

from clan_cli.ssh import Host, HostGroup, parse_deployment_address


def test_parse_ipv6() -> None:
    host = parse_deployment_address("foo", "[fe80::1%eth0]:2222")
    assert host.host == "fe80::1%eth0"
    assert host.port == 2222
    host = parse_deployment_address("foo", "[fe80::1%eth0]")
    assert host.host == "fe80::1%eth0"
    assert host.port is None


def test_run(host_group: HostGroup) -> None:
    proc = host_group.run("echo hello", stdout=subprocess.PIPE)
    assert proc[0].result.stdout == "hello\n"


def test_run_environment(host_group: HostGroup) -> None:
    p1 = host_group.run(
        "echo $env_var", stdout=subprocess.PIPE, extra_env={"env_var": "true"}
    )
    assert p1[0].result.stdout == "true\n"
    p2 = host_group.run(["env"], stdout=subprocess.PIPE, extra_env={"env_var": "true"})
    assert "env_var=true" in p2[0].result.stdout


def test_run_no_shell(host_group: HostGroup) -> None:
    proc = host_group.run(["echo", "$hello"], stdout=subprocess.PIPE)
    assert proc[0].result.stdout == "$hello\n"


def test_run_function(host_group: HostGroup) -> None:
    def some_func(h: Host) -> bool:
        p = h.run("echo hello", stdout=subprocess.PIPE)
        return p.stdout == "hello\n"

    res = host_group.run_function(some_func)
    assert res[0].result


def test_timeout(host_group: HostGroup) -> None:
    try:
        host_group.run_local("sleep 10", timeout=0.01)
    except Exception:
        pass
    else:
        raise AssertionError("should have raised TimeoutExpired")


def test_run_exception(host_group: HostGroup) -> None:
    r = host_group.run("exit 1", check=False)
    assert r[0].result.returncode == 1

    try:
        host_group.run("exit 1")
    except Exception:
        pass
    else:
        raise AssertionError("should have raised Exception")


def test_run_function_exception(host_group: HostGroup) -> None:
    def some_func(h: Host) -> subprocess.CompletedProcess[str]:
        return h.run_local("exit 1")

    try:
        host_group.run_function(some_func)
    except Exception:
        pass
    else:
        raise AssertionError("should have raised Exception")
