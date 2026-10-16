# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_spacetrack_client.py
# PATH:         space-track-data-downloader/tests/test_spacetrack_client.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for spacetrack_client.py: credential loading, login and
#               logout, retry/error handling, whoami, downloads, and cookies.
#               All HTTP goes through the FakeSession fixture in conftest.py.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import json
from pathlib import Path
import pytest
import requests
import spacetrack_client as sc
from conftest import FakeResponse, FakeSession
from spacetrack_client import (
    BASE_URL,
    SpaceTrackAuthenticationError,
    SpaceTrackConfigurationError,
    SpaceTrackCredentials,
    SpaceTrackRequestError,
)

QUERY_URL = BASE_URL + "/basicspacedata/query/class/boxscore/format/json"
CREDS = SpaceTrackCredentials(username="user@example.com", password="pw")

# =============================================================================
# Credentials
# =============================================================================

def test_no_credentials_in_environment() -> None:
    assert sc.load_credentials_from_environment() is None

def test_primary_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("SPACETRACK_USER", " alice ")
    monkeypatch.setenv("SPACETRACK_PASS", "secret")

    assert sc.load_credentials_from_environment() == SpaceTrackCredentials("alice", "secret")

def test_alias_env_vars_and_precedence(monkeypatch) -> None:
    monkeypatch.setenv("SPACE_TRACK_USERNAME", "alias-user")
    monkeypatch.setenv("SPACETRACK_PASSWORD", "alias-pass")
    assert sc.load_credentials_from_environment() == SpaceTrackCredentials("alias-user", "alias-pass")

    monkeypatch.setenv("SPACETRACK_USER", "primary-user")
    assert sc.load_credentials_from_environment().username == "primary-user"

def test_blank_env_values_are_ignored(monkeypatch) -> None:
    monkeypatch.setenv("SPACETRACK_USER", "   ")
    monkeypatch.setenv("SPACETRACK_PASS", "pw")
    assert sc.load_credentials_from_environment() is None

def test_get_credentials_prefers_environment(monkeypatch, scripted_input) -> None:
    monkeypatch.setenv("SPACETRACK_USER", "env-user")
    monkeypatch.setenv("SPACETRACK_PASS", "env-pass")

    assert sc.get_credentials() == SpaceTrackCredentials("env-user", "env-pass")
    assert scripted_input.prompts == []

def test_get_credentials_prompts_for_both(scripted_input) -> None:
    scripted_input.set("typed-user", "typed-pass")

    assert sc.get_credentials() == SpaceTrackCredentials("typed-user", "typed-pass")
    assert scripted_input.prompts == ["Username / email: ", "Password: "]

def test_get_credentials_reuses_env_username(monkeypatch, scripted_input) -> None:
    monkeypatch.setenv("SPACETRACK_USER", "env-user")
    scripted_input.set("typed-pass")

    assert sc.get_credentials() == SpaceTrackCredentials("env-user", "typed-pass")
    assert scripted_input.prompts == ["Password: "]

def test_get_credentials_without_prompt_raises() -> None:
    with pytest.raises(SpaceTrackConfigurationError):
        sc.get_credentials(allow_prompt=False)

@pytest.mark.parametrize("answers", [("", "pw"), ("user", "")])
def test_prompt_rejects_empty_values(scripted_input, answers) -> None:
    scripted_input.set(*answers)

    with pytest.raises(SpaceTrackConfigurationError):
        sc.prompt_for_credentials()

# =============================================================================
# URL checks and small helpers
# =============================================================================

@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.space-track.org/x", True),
        ("https://space-track.org/x", True),
        ("http://www.space-track.org/x", True),
        ("https://example.com/x", False),
        ("ftp://www.space-track.org/x", False),
        ("https://space-track.org.evil.com/x", False),
    ],
)
def test_is_space_track_url(url, expected) -> None:
    assert sc.is_space_track_url(url) is expected

def test_is_space_track_url_rejects_lookalike_domain() -> None:
    assert sc.is_space_track_url("https://evilspace-track.org/x") is False

@pytest.mark.xfail(reason="BUG: netloc includes the port, so an explicit :443 is rejected")
def test_is_space_track_url_accepts_explicit_port() -> None:
    assert sc.is_space_track_url("https://www.space-track.org:443/x") is True

def test_ensure_space_track_url_raises() -> None:
    with pytest.raises(SpaceTrackConfigurationError, match="Refusing"):
        sc.ensure_space_track_url("https://example.com/")

@pytest.mark.parametrize(
    "body, expected",
    [("", False), ('{"Login":"Failed"}', True), ("Invalid credentials", True), ("[]", False)],
)
def test_looks_like_login_failure(body, expected) -> None:
    assert sc.looks_like_login_failure(body) is expected

def test_response_preview_truncates() -> None:
    assert sc.response_preview("abc", max_chars=5) == "abc"
    assert sc.response_preview("abcdefgh", max_chars=5) == "abcde..."

@pytest.mark.parametrize("status", [408, 409, 425, 429, 500, 502, 503, 504])
def test_retryable_statuses(status) -> None:
    assert sc.is_retryable_status(status) is True

@pytest.mark.parametrize("status", [400, 401, 403, 404, 501])
def test_non_retryable_statuses(status) -> None:
    assert sc.is_retryable_status(status) is False

def test_response_json() -> None:
    response = sc.SpaceTrackResponse(
        url=QUERY_URL, status_code=200, text='{"a": 1}', content=b"", headers={}, elapsed_seconds=0.0
    )
    assert response.json() == {"a": 1}

# =============================================================================
# Construction
# =============================================================================

@pytest.mark.parametrize(
    "kwargs",
    [{"retries": 0}, {"timeout_seconds": 0}, {"download_timeout_seconds": -1}],
)
def test_client_rejects_invalid_settings(kwargs) -> None:
    with pytest.raises(SpaceTrackConfigurationError):
        sc.SpaceTrackClient(**kwargs)

def test_client_sets_user_agent() -> None:
    client = sc.SpaceTrackClient(user_agent="test-agent/1")
    try:
        assert client.session.headers["User-Agent"] == "test-agent/1"
        assert client.logged_in is False
    finally:
        client.close()

# =============================================================================
# Login / logout
# =============================================================================

def test_login_success(make_client) -> None:
    client = make_client([FakeResponse(200, "")])

    client.login(CREDS)

    call = client.session.calls[0]
    assert (call.method, call.url) == ("POST", BASE_URL + "/ajaxauth/login")
    assert call.kwargs["data"] == {"identity": "user@example.com", "password": "pw"}
    assert call.kwargs["timeout"] == client.timeout_seconds
    assert client.logged_in is True
    assert client.identity == "user@example.com"
    assert client.last_login_utc is not None

def test_login_http_error(make_client) -> None:
    client = make_client([FakeResponse(500, "server error")])

    with pytest.raises(SpaceTrackAuthenticationError, match="HTTP 500"):
        client.login(CREDS)

    assert client.logged_in is False

def test_login_failure_body(make_client) -> None:
    client = make_client([FakeResponse(200, '{"Login":"Failed"}')])

    with pytest.raises(SpaceTrackAuthenticationError, match="appears to have failed"):
        client.login(CREDS)

def test_login_network_error(make_client) -> None:
    client = make_client([requests.ConnectionError("down")])

    with pytest.raises(SpaceTrackAuthenticationError, match="Login request failed"):
        client.login(CREDS)

def test_logout_clears_state(make_client) -> None:
    client = make_client([FakeResponse(200, "")])
    client.logged_in, client.identity = True, "x"

    client.logout()

    assert client.session.calls[0].url == BASE_URL + "/ajaxauth/logout"
    assert (client.logged_in, client.identity) == (False, None)

def test_logout_swallows_request_errors(make_client, capsys) -> None:
    client = make_client([FakeResponse(500, "")])
    client.logged_in = True

    client.logout()

    assert client.logged_in is False
    assert "Logout request failed" in capsys.readouterr().out

def test_context_manager_logs_out_and_closes(make_client) -> None:
    client = make_client([FakeResponse(200, "")])
    client.logged_in = True

    with client:
        pass

    assert client.session.calls[0].url.endswith("/ajaxauth/logout")
    assert client.session.closed is True

def test_context_manager_skips_logout_when_logged_out(make_client) -> None:
    client = make_client([])

    with client:
        pass

    assert client.session.calls == []
    assert client.session.closed is True

# =============================================================================
# request(): success, errors, retries
# =============================================================================

def test_get_success_returns_spacetrack_response(make_client) -> None:
    client = make_client([FakeResponse(200, '[{"x": 1}]', headers={"Content-Type": "application/json"}, url=QUERY_URL)])

    response = client.get(QUERY_URL, timeout_seconds=7)

    assert response.status_code == 200
    assert response.json() == [{"x": 1}]
    assert response.content == b'[{"x": 1}]'
    assert response.headers == {"Content-Type": "application/json"}
    assert response.url == QUERY_URL
    assert response.elapsed_seconds >= 0

    call = client.session.calls[0]
    assert (call.method, call.url) == ("GET", QUERY_URL)
    assert call.kwargs["timeout"] == 7
    assert call.kwargs["stream"] is False

def test_default_timeout_used(make_client) -> None:
    client = make_client([FakeResponse(200, "")], timeout_seconds=11)
    client.get(QUERY_URL)
    assert client.session.calls[0].kwargs["timeout"] == 11

def test_post_forwards_kwargs(make_client) -> None:
    client = make_client([FakeResponse(200, "")])
    client.post(QUERY_URL, data={"a": "b"})

    call = client.session.calls[0]
    assert call.method == "POST"
    assert call.kwargs["data"] == {"a": "b"}

def test_non_space_track_url_refused_before_any_request(make_client) -> None:
    client = make_client([])

    with pytest.raises(SpaceTrackConfigurationError):
        client.get("https://example.com/data")

    assert client.session.calls == []

def test_non_space_track_url_allowed_when_opted_in(make_client) -> None:
    client = make_client([FakeResponse(200, "ok")])
    assert client.get("https://example.com/data", allow_non_space_track_url=True).text == "ok"

def test_401_clears_login_and_is_not_retried(make_client, sleep_calls) -> None:
    client = make_client([FakeResponse(401, "")])
    client.logged_in = True

    with pytest.raises(SpaceTrackAuthenticationError, match="401"):
        client.get(QUERY_URL)

    assert client.logged_in is False
    assert len(client.session.calls) == 1
    assert sleep_calls == []

def test_403_is_not_retried(make_client, sleep_calls) -> None:
    client = make_client([FakeResponse(403, "")])
    client.logged_in = True

    with pytest.raises(SpaceTrackAuthenticationError, match="403"):
        client.get(QUERY_URL)

    assert client.logged_in is True
    assert len(client.session.calls) == 1
    assert sleep_calls == []

def test_404_raises_immediately(make_client, sleep_calls) -> None:
    client = make_client([FakeResponse(404, "not here")])

    with pytest.raises(SpaceTrackRequestError, match="HTTP 404.*not here"):
        client.get(QUERY_URL)

    assert sleep_calls == []

def test_retryable_status_then_success(make_client, sleep_calls) -> None:
    client = make_client([FakeResponse(503, "busy"), FakeResponse(429, "slow down"), FakeResponse(200, "ok")])

    response = client.get(QUERY_URL)

    assert response.text == "ok"
    assert len(client.session.calls) == 3
    assert sleep_calls == [5.0, 10.0]

def test_retryable_status_exhausts_retries(make_client, sleep_calls) -> None:
    client = make_client([FakeResponse(503, "busy")] * 3)

    with pytest.raises(SpaceTrackRequestError, match="HTTP 503"):
        client.get(QUERY_URL)

    assert len(client.session.calls) == 3
    assert sleep_calls == [5.0, 10.0]

@pytest.mark.parametrize("error", [requests.Timeout("slow"), requests.ConnectionError("down")])
def test_network_errors_are_retried(make_client, sleep_calls, error) -> None:
    client = make_client([error, FakeResponse(200, "ok")])

    assert client.get(QUERY_URL).text == "ok"
    assert sleep_calls == [5.0]

def test_network_errors_exhaust_retries(make_client, sleep_calls) -> None:
    client = make_client([requests.Timeout("slow")] * 2, retries=2, retry_delay_seconds=1.5)

    with pytest.raises(SpaceTrackRequestError, match="after 2 attempts.*slow"):
        client.get(QUERY_URL)

    assert sleep_calls == [1.5]

# =============================================================================
# Convenience request helpers
# =============================================================================

def test_download_text_and_bytes_use_download_timeout(make_client) -> None:
    client = make_client(
        [FakeResponse(200, "text body"), FakeResponse(200, "", content=b"\x00\x01")],
        download_timeout_seconds=99,
    )

    assert client.download_text(QUERY_URL) == "text body"
    assert client.download_bytes(QUERY_URL) == b"\x00\x01"
    assert [c.kwargs["timeout"] for c in client.session.calls] == [99, 99]

def test_get_json(make_client) -> None:
    client = make_client([FakeResponse(200, '{"ok": true}'), FakeResponse(200, "<html>")])

    assert client.get_json(QUERY_URL) == {"ok": True}

    with pytest.raises(SpaceTrackRequestError, match="Could not parse"):
        client.get_json(QUERY_URL)

# =============================================================================
# whoami / session status
# =============================================================================

def test_whoami_logged_in(make_client) -> None:
    body = json.dumps({"logged_in": True, "identity": "alice", "session_expiration": "2026-10-15T14:00:00"})
    client = make_client([FakeResponse(200, body)])

    info = client.whoami()

    assert client.session.calls[0].url == BASE_URL + "/app/data/whoami"
    assert (info.logged_in, info.identity, info.session_expiration) == (True, "alice", "2026-10-15T14:00:00")
    assert (client.logged_in, client.identity) == (True, "alice")

def test_whoami_logged_out_clears_identity(make_client) -> None:
    client = make_client([FakeResponse(200, '{"logged_in": false}')])
    client.identity = "stale"

    info = client.whoami()

    assert info.logged_in is False
    assert client.identity is None

@pytest.mark.parametrize("body", ["not json", "[1, 2]"])
def test_whoami_bad_body(make_client, body) -> None:
    client = make_client([FakeResponse(200, body)])

    with pytest.raises(SpaceTrackRequestError):
        client.whoami()

def test_ensure_logged_in(make_client) -> None:
    client = make_client([FakeResponse(200, '{"logged_in": true}'), FakeResponse(200, '{"logged_in": false}')])

    client.ensure_logged_in()

    with pytest.raises(SpaceTrackAuthenticationError):
        client.ensure_logged_in()

def test_print_session_status(make_client, capsys) -> None:
    client = make_client([FakeResponse(200, '{"logged_in": true, "identity": "alice"}'), FakeResponse(500, "")], retries=1)

    client.print_session_status()
    assert "alice" in capsys.readouterr().out

    client.print_session_status()
    assert "Could not check session status" in capsys.readouterr().out

# =============================================================================
# download_to_file
# =============================================================================

def test_download_to_file_streams_chunks(make_client, tmp_path: Path) -> None:
    client = make_client([FakeResponse(200, chunks=[b"abc", b"", b"def"])])
    target = tmp_path / "deep" / "file.bin"

    result = client.download_to_file(QUERY_URL, target, chunk_size=3)

    assert result == target
    assert target.read_bytes() == b"abcdef"
    assert client.session.calls[0].kwargs["stream"] is True

def test_download_to_file_retries_then_succeeds(make_client, tmp_path: Path, sleep_calls) -> None:
    client = make_client([FakeResponse(502, "bad gateway"), FakeResponse(200, chunks=[b"ok"])])

    client.download_to_file(QUERY_URL, tmp_path / "f.bin")

    assert (tmp_path / "f.bin").read_bytes() == b"ok"
    assert sleep_calls == [5.0]

def test_download_to_file_auth_error_writes_nothing(make_client, tmp_path: Path) -> None:
    client = make_client([FakeResponse(401, "")])

    with pytest.raises(SpaceTrackAuthenticationError):
        client.download_to_file(QUERY_URL, tmp_path / "f.bin")

    assert not (tmp_path / "f.bin").exists()

def test_download_to_file_refuses_foreign_url(make_client, tmp_path: Path) -> None:
    client = make_client([])

    with pytest.raises(SpaceTrackConfigurationError):
        client.download_to_file("https://example.com/f", tmp_path / "f.bin")

def test_download_to_file_exhausts_retries(make_client, tmp_path: Path) -> None:
    client = make_client([requests.ConnectionError("down")] * 3)

    with pytest.raises(SpaceTrackRequestError, match="after 3 attempts"):
        client.download_to_file(QUERY_URL, tmp_path / "f.bin")

# =============================================================================
# Cookies
# =============================================================================

def test_save_cookies(make_client, tmp_path: Path) -> None:
    client = make_client([])
    client.session.cookies.set("chocolatechip", "abc", domain="www.space-track.org", path="/")

    path = client.save_cookies(tmp_path / "c" / "cookies.json")
    cookies = json.loads(path.read_text())

    assert cookies == [
        {
            "name": "chocolatechip",
            "value": "abc",
            "domain": "www.space-track.org",
            "path": "/",
            "expires": None,
            "secure": False,
        }
    ]

# =============================================================================
# create_logged_in_client
# =============================================================================

def test_create_logged_in_client_success(monkeypatch) -> None:
    session = FakeSession([FakeResponse(200, "")])
    monkeypatch.setattr(sc.requests, "Session", lambda: session)
    monkeypatch.setenv("SPACETRACK_USER", "env-user")
    monkeypatch.setenv("SPACETRACK_PASS", "env-pass")

    client = sc.create_logged_in_client(allow_prompt=False, retries=2)

    assert client.logged_in is True
    assert client.retries == 2
    assert session.calls[0].kwargs["data"] == {"identity": "env-user", "password": "env-pass"}
    assert session.closed is False

def test_create_logged_in_client_closes_session_on_failure(monkeypatch) -> None:
    session = FakeSession([FakeResponse(200, "Login Failed")])
    monkeypatch.setattr(sc.requests, "Session", lambda: session)
    monkeypatch.setenv("SPACETRACK_USER", "u")
    monkeypatch.setenv("SPACETRACK_PASS", "p")

    with pytest.raises(SpaceTrackAuthenticationError):
        sc.create_logged_in_client(allow_prompt=False)

    assert session.closed is True

def test_create_logged_in_client_missing_credentials(monkeypatch) -> None:
    session = FakeSession([])
    monkeypatch.setattr(sc.requests, "Session", lambda: session)

    with pytest.raises(SpaceTrackConfigurationError):
        sc.create_logged_in_client(allow_prompt=False)

    assert session.calls == []
    assert session.closed is True

# =============================================================================
# Network guard
# =============================================================================

def test_real_network_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="Network access attempted"):
        requests.get("https://www.space-track.org/ajaxauth/login", timeout=1)
