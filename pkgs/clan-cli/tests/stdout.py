import types

import pytest


class CaptureOutput:
    def __init__(self, capsys: pytest.CaptureFixture) -> None:
        self.capsys = capsys
        self.capsys_disabled = capsys.disabled()
        self.capsys_disabled.__enter__()

    def __enter__(self) -> "CaptureOutput":
        self.capsys_disabled.__exit__(None, None, None)
        self.capsys.readouterr()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        res = self.capsys.readouterr()
        self.out = res.out
        self.err = res.err

        # Disable capsys again
        self.capsys_disabled = self.capsys.disabled()
        self.capsys_disabled.__enter__()


@pytest.fixture
def capture_output(capsys: pytest.CaptureFixture) -> CaptureOutput:
    return CaptureOutput(capsys)
