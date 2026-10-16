# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_spacetrack_gui.py
# PATH:         space-track-data-downloader/tests/test_spacetrack_gui.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for spacetrack_gui.py through FastAPI's TestClient: page
#               and token, Host/token/content-type guards, login without
#               keeping the password, offline preview, download, and history.
#               The Space-Track client is real but backed by a FakeSession.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import spacetrack_gui
from conftest import FakeResponse

PASSWORD = "s3cret-Pa55word"
BASE_URL = "http://127.0.0.1:8765"

@pytest.fixture
def gui(make_client):
    """
    Build the app with a queue of fake Space-Track responses.

    Returns (TestClient, state, sessions); sessions lists every FakeSession
    the app created, so tests can count HTTP calls.
    """
    sessions: list[Any] = []
    queue: list[FakeResponse | Exception] = []

    def factory():
        client = make_client(retries=1)
        client.session.queue = queue  # share one queue so tests can add responses later
        sessions.append(client.session)
        return client

    app = spacetrack_gui.create_app(client_factory=factory)
    test_client = TestClient(app, base_url=BASE_URL)
    state = app.state.gui
    test_client.headers.update({"x-gui-token": state.token})

    with test_client:
        yield test_client, state, sessions, queue
        queue.append(FakeResponse(200, ""))  # shutdown logs out a live session

def calls(sessions) -> list[str]:
    return [f"{c.method} {c.url}" for s in sessions for c in s.calls]

def log_in(test_client, queue) -> None:
    queue.append(FakeResponse(200, '""'))
    assert test_client.post("/api/login", json={"username": "me@example.com", "password": PASSWORD}).status_code == 200

def gp_body(**extra: Any) -> dict[str, Any]:
    body = {"dataset_key": "gp", "values": {"object_type": "debris_on_orbit"}, "query_options": {"limit": 5, "show_empty": False}}
    body.update(extra)
    return body

# =============================================================================
# Page, guards, and headers
# =============================================================================

def test_index_injects_token_and_sets_security_headers(gui) -> None:
    test_client, state, _, _ = gui

    page = test_client.get("/")

    assert page.status_code == 200
    assert f'content="{state.token}"' in page.text
    assert "__GUI_TOKEN__" not in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert page.headers["x-frame-options"] == "DENY"
    assert test_client.get("/static/app.js").status_code == 200

def test_tokens_differ_per_app() -> None:
    assert spacetrack_gui.create_app().state.gui.token != spacetrack_gui.create_app().state.gui.token

@pytest.mark.parametrize("host", ["evil.example:8765", "127.0.0.1:9999", "localhost", ""])
def test_foreign_host_rejected(gui, host) -> None:
    test_client, _, _, _ = gui
    assert test_client.get("/api/session", headers={"host": host}).status_code == 400

def test_localhost_host_allowed(gui) -> None:
    test_client, _, _, _ = gui
    assert test_client.get("/api/session", headers={"host": "localhost:8765"}).status_code == 200

def test_post_without_token_rejected(gui) -> None:
    test_client, _, sessions, _ = gui

    response = test_client.post("/api/login", json={"username": "a", "password": "b"}, headers={"x-gui-token": "wrong"})

    assert response.status_code == 403
    assert calls(sessions) == []

def test_post_requires_json(gui) -> None:
    test_client, _, sessions, _ = gui

    response = test_client.post("/api/login", content="username=a&password=b", headers={"content-type": "application/x-www-form-urlencoded"})

    assert response.status_code == 415
    assert calls(sessions) == []

def test_api_responses_are_not_cached(gui) -> None:
    test_client, _, _, _ = gui
    assert test_client.get("/api/session").headers["cache-control"] == "no-store"

def test_main_binds_to_loopback(monkeypatch) -> None:
    import uvicorn

    seen: dict[str, Any] = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    monkeypatch.setattr(spacetrack_gui.threading, "Timer", lambda *a, **k: type("T", (), {"start": lambda self: None})())

    assert spacetrack_gui.main() == 0
    assert (seen["host"], seen["port"]) == ("127.0.0.1", 8765)

# =============================================================================
# Session
# =============================================================================

def test_session_starts_logged_out_without_network(gui) -> None:
    test_client, _, sessions, _ = gui

    assert test_client.get("/api/session").json() == {"logged_in": False, "identity": None, "last_login_utc": None}
    assert calls(sessions) == []

def test_login_keeps_no_password(gui) -> None:
    test_client, state, sessions, queue = gui

    log_in(test_client, queue)

    assert test_client.get("/api/session").json()["identity"] == "me@example.com"
    assert calls(sessions) == ["POST https://www.space-track.org/ajaxauth/login"]

    def contains_password(obj: Any, depth: int = 0) -> bool:
        if depth > 3:
            return False
        if isinstance(obj, str):
            return PASSWORD in obj
        if isinstance(obj, dict):
            return any(contains_password(v, depth + 1) for v in obj.values())
        if isinstance(obj, (list, tuple)):
            return any(contains_password(v, depth + 1) for v in obj)
        if hasattr(obj, "__dict__"):
            return any(contains_password(v, depth + 1) for k, v in vars(obj).items() if k != "calls")
        return False

    assert not contains_password(state)

def test_login_failure_returns_401(gui) -> None:
    test_client, state, _, queue = gui
    queue.append(FakeResponse(200, '{"Login": "Failed"}'))

    response = test_client.post("/api/login", json={"username": "me", "password": PASSWORD})

    assert response.status_code == 401
    assert PASSWORD not in response.text
    assert state.client is None

def test_login_validation(gui) -> None:
    test_client, _, sessions, _ = gui

    assert test_client.post("/api/login", json={"username": "", "password": "x"}).status_code == 422
    assert test_client.post("/api/login", json={"username": "  ", "password": "x"}).status_code == 400
    assert calls(sessions) == []

def test_logout_ends_session(gui) -> None:
    test_client, state, sessions, queue = gui
    log_in(test_client, queue)
    queue.append(FakeResponse(200, ""))

    assert test_client.post("/api/logout", json={}).json()["logged_in"] is False
    assert state.client is None
    assert sessions[0].closed

# =============================================================================
# Datasets and preview (offline)
# =============================================================================

def test_datasets_and_dataset_description(gui) -> None:
    test_client, _, sessions, _ = gui

    groups = test_client.get("/api/datasets").json()["groups"]
    gp = test_client.get("/api/datasets/gp").json()

    assert any(d["key"] == "gp" for g in groups for d in g["datasets"])
    assert gp["fields"][0]["id"] == "object_type"
    assert test_client.get("/api/datasets/nope").status_code == 404
    assert calls(sessions) == []

def test_preview_builds_url_without_network(gui) -> None:
    test_client, _, sessions, _ = gui

    response = test_client.post("/api/preview", json=gp_body())

    assert response.status_code == 200
    assert response.json()["url"] == (
        "https://www.space-track.org/basicspacedata/query/class/gp"
        "/OBJECT_TYPE/DEBRIS/DECAY_DATE/null-val/orderby/NORAD_CAT_ID/limit/5/format/json"
    )
    assert calls(sessions) == []

def test_preview_reports_tle_warning(gui) -> None:
    test_client, _, _, _ = gui
    body = gp_body(query_options={"output_format": "tle"})
    assert test_client.post("/api/preview", json=body).json()["warnings"]

@pytest.mark.parametrize(
    "body, status",
    [
        ({"dataset_key": "nope"}, 404),
        ({"dataset_key": "gp", "values": {"bogus": 1}}, 400),
        ({"dataset_key": "gp", "query_options": {"output_format": "pdf"}}, 400),
        ({"dataset_key": "gp", "query_options": {"offset": 2}}, 400),
    ],
)
def test_preview_errors(gui, body, status) -> None:
    test_client, _, _, _ = gui
    response = test_client.post("/api/preview", json=body)
    assert response.status_code == status
    assert response.json()["error"]

# =============================================================================
# Download
# =============================================================================

def test_download_requires_login(gui) -> None:
    test_client, _, sessions, _ = gui
    assert test_client.post("/api/download", json=gp_body()).status_code == 401
    assert calls(sessions) == []

def test_download_writes_file_metadata_and_preview(gui) -> None:
    test_client, _, sessions, queue = gui
    log_in(test_client, queue)
    queue.append(FakeResponse(200, '[{"NORAD_CAT_ID": "25544", "OBJECT_NAME": "ISS"}]', headers={"Set-Cookie": "x"}))

    response = test_client.post("/api/download", json=gp_body(export={"download_dir": "gui", "custom_name": "my run"}))

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["file"]["filename"] == "my_run.json"
    assert Path(data["file"]["path"]) == Path("downloads/gui/my_run.json")
    assert data["preview"]["table"]["rows"] == [["25544", "ISS"]]
    assert data["metadata_error"] is None
    meta = json.loads(Path(data["metadata_file"]).read_text())
    assert meta["query_url"] == data["url"]
    assert "Set-Cookie" not in (meta["response_headers"] or {})
    assert calls(sessions)[-1].startswith("GET https://www.space-track.org/basicspacedata/query/class/gp/")

def test_download_dir_must_stay_inside_downloads(gui) -> None:
    test_client, _, sessions, queue = gui
    log_in(test_client, queue)

    response = test_client.post("/api/download", json=gp_body(export={"download_dir": "../outside"}))

    assert response.status_code == 400
    assert len(calls(sessions)) == 1  # only the login

def test_download_refuses_redirect_off_space_track(gui) -> None:
    test_client, _, _, queue = gui
    log_in(test_client, queue)
    queue.append(FakeResponse(200, "[]", url="https://evil.example/x"))

    response = test_client.post("/api/download", json=gp_body())

    assert response.status_code == 502
    assert not Path("downloads").exists() or not any(Path("downloads").iterdir())

def test_download_busy_returns_409(gui) -> None:
    test_client, state, _, queue = gui
    log_in(test_client, queue)
    state.download_lock.acquire()

    try:
        assert test_client.post("/api/download", json=gp_body()).status_code == 409
    finally:
        state.download_lock.release()

# =============================================================================
# History
# =============================================================================

def test_history_lists_downloads_and_previews(gui) -> None:
    test_client, _, sessions, queue = gui
    log_in(test_client, queue)
    queue.append(FakeResponse(200, "A,B\n1,2\n"))
    test_client.post("/api/download", json=gp_body(query_options={"output_format": "csv"}))
    before = len(calls(sessions))

    entries = test_client.get("/api/history").json()["entries"]

    assert len(entries) == 1 and entries[0]["output_format"] == "csv"
    preview = test_client.get("/api/history/preview", params={"meta_file": entries[0]["meta_file"]}).json()
    assert preview["table"] == {"columns": ["A", "B"], "rows": [["1", "2"]], "total": 1}
    assert len(calls(sessions)) == before

@pytest.mark.parametrize("meta_file", ["../secrets_meta.json", "/etc/passwd", "downloads/x.json"])
def test_history_preview_refuses_outside_paths(gui, meta_file) -> None:
    test_client, _, _, _ = gui
    assert test_client.get("/api/history/preview", params={"meta_file": meta_file}).status_code == 400

def test_static_files_do_not_expose_source(gui) -> None:
    test_client, _, _, _ = gui
    assert test_client.get("/static/../spacetrack_gui.py").status_code == 404
    assert test_client.get("/static/%2e%2e/spacetrack_gui.py").status_code == 404
