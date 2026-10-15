# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         conftest.py
# PATH:         space-track-data-downloader/tests/conftest.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Shared pytest fixtures. Blocks all real network access, isolates
#               the working directory and credential environment, and provides
#               fake HTTP sessions/responses and scripted terminal input.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import pytest
import requests
import spacetrack_client

FIXTURES_DIR = Path(__file__).parent / "fixtures"

CREDENTIAL_ENV_KEYS = (
    spacetrack_client.ENV_USERNAME_KEYS + spacetrack_client.ENV_PASSWORD_KEYS
)

# =============================================================================
# Autouse safety fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Fail loudly if any test reaches the real requests transport layer.
    """
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network access attempted during tests.")

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", refuse)

@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Run every test from tmp_path with no Space-Track credentials set.

    The exporters default to a CWD-relative downloads/ directory, so changing
    directory keeps stray writes out of the repository's downloads/ folder.
    """
    monkeypatch.chdir(tmp_path)

    for key in CREDENTIAL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    # RuntimeMetadata binds getpass.getuser at class definition, so the
    # environment is the only reliable way to make the username predictable.
    monkeypatch.setenv("LOGNAME", "tester")

@pytest.fixture(autouse=True)
def sleep_calls(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """
    Replace retry sleeps with a recorder. Returns the list of delays.
    """
    calls: list[float] = []
    monkeypatch.setattr(spacetrack_client.time, "sleep", calls.append)
    return calls

# =============================================================================
# Fake HTTP layer
# =============================================================================

class FakeResponse:
    """
    Minimal stand-in for requests.Response covering every attribute that
    spacetrack_client reads.
    """

    def __init__(
        self,
        status_code: int = 200,
        text: str = "",
        *,
        content: bytes | None = None,
        headers: dict[str, str] | None = None,
        url: str = "https://www.space-track.org/fake",
        chunks: list[bytes] | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")
        self.headers = headers or {}
        self.url = url
        self._chunks = chunks

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size: int = 1) -> Any:
        if self._chunks is not None:
            yield from self._chunks
        else:
            yield self.content

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

@dataclass
class RecordedCall:
    method: str
    url: str
    kwargs: dict[str, Any] = field(default_factory=dict)

class FakeSession:
    """
    Replacement for requests.Session.

    Each request pops the next queued item. A FakeResponse is returned; an
    exception instance is raised.
    """

    def __init__(self, queue: list[FakeResponse | Exception] | None = None) -> None:
        self.queue = list(queue or [])
        self.calls: list[RecordedCall] = []
        self.headers: dict[str, str] = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.closed = False

    def _next(self, method: str, url: str, kwargs: dict[str, Any]) -> FakeResponse:
        self.calls.append(RecordedCall(method=method, url=url, kwargs=kwargs))

        if not self.queue:
            raise AssertionError(f"FakeSession has no queued response for {method} {url}")

        item = self.queue.pop(0)

        if isinstance(item, Exception):
            raise item

        return item

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        return self._next(method.upper(), url, kwargs)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("GET", url, kwargs)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._next("POST", url, kwargs)

    def close(self) -> None:
        self.closed = True

@pytest.fixture
def make_client():
    """
    Factory: build a real SpaceTrackClient whose session is a FakeSession.
    """
    def factory(
        queue: list[FakeResponse | Exception] | None = None,
        **client_kwargs: Any,
    ) -> spacetrack_client.SpaceTrackClient:
        client = spacetrack_client.SpaceTrackClient(**client_kwargs)
        client.session.close()
        client.session = FakeSession(queue)
        return client

    return factory

# =============================================================================
# Scripted terminal input
# =============================================================================

class ScriptedInput:
    """
    Feeds a fixed list of answers to input()/getpass() and records prompts.
    """

    def __init__(self) -> None:
        self.answers: list[str] = []
        self.prompts: list[str] = []
        self.strict = True

    def set(self, *answers: str) -> None:
        self.answers = list(answers)

    def enter_for_all(self, limit: int = 60) -> None:
        """
        Press Enter at every prompt, without requiring the script to be used
        up. For tests whose prompt count may change when a bug is fixed.
        """
        self.answers = [""] * limit
        self.strict = False

    def __call__(self, prompt: str = "") -> str:
        self.prompts.append(prompt)

        if not self.answers:
            raise AssertionError(f"Ran out of scripted input at prompt: {prompt!r}")

        return self.answers.pop(0)

@pytest.fixture
def scripted_input(monkeypatch: pytest.MonkeyPatch):
    """
    Patch input() and getpass.getpass() with scripted answers.

    Call scripted_input.set("answer1", "answer2", ...). The test fails at
    teardown if any answers were left unused.
    """
    scripted = ScriptedInput()
    monkeypatch.setattr("builtins.input", scripted)
    monkeypatch.setattr(spacetrack_client.getpass, "getpass", scripted)

    yield scripted

    assert not scripted.strict or scripted.answers == [], (
        f"Unused scripted answers: {scripted.answers!r}. "
        f"Prompts seen: {scripted.prompts!r}"
    )

@pytest.fixture
def fixture_text():
    """
    Read a file from tests/fixtures as text.
    """
    def read(name: str) -> str:
        return (FIXTURES_DIR / name).read_text(encoding="utf-8")

    return read
