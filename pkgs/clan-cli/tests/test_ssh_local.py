from clan_cli.async_run import AsyncRuntime
from clan_cli.cmd import ClanCmdTimeoutError, Log, RunOpts
from clan_cli.ssh.host import Host

host = Host("some_host")


def test_run_environment(runtime: AsyncRuntime) -> None:
    p2 = runtime.async_run(
        None,
        host.run_local,
        ["echo $env_var"],
        RunOpts(shell=True, log=Log.STDERR),
        extra_env={"env_var": "true"},
    )

    assert p2.wait().result.stdout == "true\n"

    p3 = runtime.async_run(
        None,
        host.run_local,
        ["env"],
        RunOpts(shell=True, log=Log.STDERR),
        extra_env={"env_var": "true"},
    )
    assert "env_var=true" in p3.wait().result.stdout


def test_run_local(runtime: AsyncRuntime) -> None:
    p1 = runtime.async_run(
        None, host.run_local, ["echo", "hello"], RunOpts(log=Log.STDERR)
    )
    assert p1.wait().result.stdout == "hello\n"


def test_timeout(runtime: AsyncRuntime) -> None:
    p1 = runtime.async_run(None, host.run_local, ["sleep", "10"], RunOpts(timeout=0.01))
    error = p1.wait().error
    assert isinstance(error, ClanCmdTimeoutError)


def test_run_exception(runtime: AsyncRuntime) -> None:
    p1 = runtime.async_run(None, host.run_local, ["exit 1"], RunOpts(shell=True))
    assert p1.wait().error is not None


def test_run_local_non_shell(runtime: AsyncRuntime) -> None:
    p2 = runtime.async_run(None, host.run_local, ["echo", "1"], RunOpts(log=Log.STDERR))
    assert p2.wait().result.stdout == "1\n"
