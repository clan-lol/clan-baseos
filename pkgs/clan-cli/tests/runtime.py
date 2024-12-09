import pytest
from clan_cli.async_run import AsyncRuntime


@pytest.fixture
def runtime() -> AsyncRuntime:
    return AsyncRuntime()
