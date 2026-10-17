# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         spacetrack_gui.py
# PATH:         space-track-data-downloader/spacetrack_gui.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Local web GUI. Serves a FastAPI app on 127.0.0.1:8765 over the
#               same downloader_core the terminal wizard uses. The Space-Track
#               session lives only in server memory; passwords are never kept.
#               Only login and an explicit download click contact Space-Track.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations

import secrets
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException

from downloader_core import (
    CoreError,
    build_filter_config,
    dataset_catalog,
    describe_dataset,
    export_download,
    fetch,
    format_warning,
    list_download_history,
    normalize_query_options,
    null_value_hints,
    prepare_query,
    read_output_preview,
    resolve_download_dir,
    save_download_metadata,
)
from exporters import DEFAULT_DOWNLOAD_DIR
from metadata import MetadataError, read_metadata_file
from query_builder import QueryBuilderError
from spacetrack_client import (
    SpaceTrackAuthenticationError,
    SpaceTrackClient,
    SpaceTrackClientError,
    SpaceTrackCredentials,
)

HOST = "127.0.0.1"
PORT = 8765
APP_URL = f"http://{HOST}:{PORT}/"
STATIC_DIR = Path(__file__).resolve().parent / "gui" / "static"
TOKEN_PLACEHOLDER = "__GUI_TOKEN__"
TOKEN_HEADER = "x-gui-token"
ALLOWED_HOSTS = frozenset({f"127.0.0.1:{PORT}", f"localhost:{PORT}"})

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "base-uri 'none'",
        "form-action 'none'",
    ]
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# =============================================================================
# Request bodies
# =============================================================================

class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024, repr=False)

class QueryBody(BaseModel):
    dataset_key: str
    values: dict[str, Any] = Field(default_factory=dict)
    query_options: dict[str, Any] = Field(default_factory=dict)

class ExportBody(BaseModel):
    download_dir: str | None = None
    custom_name: str | None = None
    overwrite: bool = False
    pretty_json: bool = True

class DownloadBody(QueryBody):
    export: ExportBody = Field(default_factory=ExportBody)

# =============================================================================
# Session state
# =============================================================================

class GuiState:
    """
    In-memory server state: one Space-Track session and a CSRF token.

    Credentials are never stored here; only the logged-in client's cookie
    session is kept, and only until logout or shutdown.
    """

    def __init__(self, client_factory: Callable[[], SpaceTrackClient]) -> None:
        self.client_factory = client_factory
        self.client: SpaceTrackClient | None = None
        self.token = secrets.token_urlsafe(32)
        self.session_lock = threading.Lock()
        self.download_lock = threading.Lock()

    def session_info(self) -> dict[str, Any]:
        client = self.client

        if client is None or not client.logged_in:
            return {"logged_in": False, "identity": None, "last_login_utc": None}

        return {
            "logged_in": True,
            "identity": client.identity,
            "last_login_utc": client.last_login_utc,
        }

    def close_client(self) -> None:
        client, self.client = self.client, None

        if client is None:
            return

        try:
            if client.logged_in:
                client.logout()
        finally:
            client.close()

def fail(status_code: int, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=message)

# =============================================================================
# App factory
# =============================================================================

def create_app(
    *,
    client_factory: Callable[[], SpaceTrackClient] = SpaceTrackClient,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    allowed_hosts: frozenset[str] = ALLOWED_HOSTS,
) -> FastAPI:
    """
    Build the GUI app. Tests pass a fake client_factory.
    """
    state = GuiState(client_factory)
    base_dir = Path(download_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        with state.session_lock:
            state.close_client()

    app = FastAPI(
        title="Space-Track Data Downloader",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.gui = state

    # -------------------------------------------------------------------------
    # Middleware and error handling
    # -------------------------------------------------------------------------

    @app.middleware("http")
    async def guard(request: Request, call_next: Callable) -> Response:
        # Host allowlist: blocks DNS-rebinding pages from reaching the API.
        if request.headers.get("host", "") not in allowed_hosts:
            return JSONResponse({"error": "Host not allowed."}, status_code=400)

        if request.method not in {"GET", "HEAD"}:
            token = request.headers.get(TOKEN_HEADER, "")

            if not secrets.compare_digest(token, state.token):
                return JSONResponse({"error": "Missing or invalid GUI token."}, status_code=403)

            content_type = request.headers.get("content-type", "").split(";")[0].strip()

            if content_type != "application/json":
                return JSONResponse({"error": "Expected a JSON body."}, status_code=415)

        response = await call_next(request)

        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)

        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"

        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in err.get("loc", ())[1:]) for err in exc.errors()})
        return JSONResponse({"error": f"Invalid request: {', '.join(fields) or 'body'}"}, status_code=422)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def prepare(body: QueryBody):
        try:
            filter_config = build_filter_config(body.dataset_key, body.values)
            query_options = normalize_query_options(body.dataset_key, body.query_options)
            prepared = prepare_query(
                dataset_key=body.dataset_key,
                filters=filter_config["filters"],
                favorites=filter_config.get("favorites"),
                publicfiles_download_name=filter_config.get("publicfiles_download_name"),
                query_options=query_options,
            )
        except KeyError as exc:
            raise fail(404, f"Unknown dataset: {body.dataset_key}") from exc
        except (CoreError, QueryBuilderError, ValueError) as exc:
            raise fail(400, str(exc)) from exc

        return filter_config, query_options, prepared

    def preview_payload(filter_config: dict[str, Any], query_options: dict[str, Any], prepared: Any) -> dict[str, Any]:
        warning = format_warning(prepared.dataset_key, prepared.output_format)

        return {
            "url": prepared.url,
            "summary": prepared.summary,
            "filters": filter_config["filters"],
            "favorites": filter_config.get("favorites"),
            "query_options": query_options,
            "warnings": [warning] if warning else [],
        }

    # -------------------------------------------------------------------------
    # Page
    # -------------------------------------------------------------------------

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html.replace(TOKEN_PLACEHOLDER, state.token), headers={"Cache-Control": "no-store"})

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # -------------------------------------------------------------------------
    # Session (only /api/login and /api/download reach Space-Track)
    # -------------------------------------------------------------------------

    @app.get("/api/session")
    def session() -> dict[str, Any]:
        return state.session_info()

    @app.post("/api/login")
    def login(body: LoginBody) -> dict[str, Any]:
        username = body.username.strip()

        if not username:
            raise fail(400, "Username is required.")

        with state.session_lock:
            state.close_client()
            client = state.client_factory()

            try:
                client.login(SpaceTrackCredentials(username=username, password=body.password))
            except SpaceTrackAuthenticationError as exc:
                client.close()
                raise fail(401, "Login failed. Check your Space-Track username and password.") from exc
            except SpaceTrackClientError as exc:
                client.close()
                raise fail(502, f"Could not reach Space-Track: {exc}") from exc

            state.client = client

        return state.session_info()

    @app.post("/api/logout")
    def logout() -> dict[str, Any]:
        with state.session_lock:
            state.close_client()

        return state.session_info()

    # -------------------------------------------------------------------------
    # Datasets and offline query preview
    # -------------------------------------------------------------------------

    @app.get("/api/datasets")
    def datasets() -> dict[str, Any]:
        return {"groups": dataset_catalog()}

    @app.get("/api/datasets/{dataset_key}")
    def dataset(dataset_key: str) -> dict[str, Any]:
        try:
            return describe_dataset(dataset_key)
        except KeyError as exc:
            raise fail(404, f"Unknown dataset: {dataset_key}") from exc

    @app.post("/api/preview")
    def preview(body: QueryBody) -> dict[str, Any]:
        return {**preview_payload(*prepare(body)), "value_hints": null_value_hints(body.values)}

    # -------------------------------------------------------------------------
    # Download (the only Space-Track data request, sent on an explicit click)
    # -------------------------------------------------------------------------

    @app.post("/api/download")
    def download(body: DownloadBody) -> dict[str, Any]:
        filter_config, query_options, prepared = prepare(body)

        try:
            target_dir = resolve_download_dir(body.export.download_dir, base_dir)
        except CoreError as exc:
            raise fail(400, str(exc)) from exc

        client = state.client

        if client is None or not client.logged_in:
            raise fail(401, "Log in to Space-Track first.")

        if not state.download_lock.acquire(blocking=False):
            raise fail(409, "A download is already running.")

        try:
            try:
                response = fetch(client, prepared.url)
            except SpaceTrackAuthenticationError as exc:
                raise fail(401, f"Authentication error: {exc}") from exc
            except SpaceTrackClientError as exc:
                raise fail(502, f"Request failed: {exc}") from exc

            export_options = {
                "download_dir": target_dir,
                "custom_name": (body.export.custom_name or "").strip() or None,
                "overwrite": body.export.overwrite,
                "pretty_json": body.export.pretty_json,
            }

            try:
                result = export_download(
                    response=response,
                    dataset_key=prepared.dataset_key,
                    output_format=prepared.output_format,
                    publicfiles_download_name=prepared.publicfiles_download_name,
                    export_options=export_options,
                )
            except Exception as exc:
                raise fail(500, f"Failed to export response: {exc}") from exc

            metadata_file = None
            metadata_error = None

            try:
                metadata_file = str(
                    save_download_metadata(
                        prepared=prepared,
                        export_result=result,
                        response=response,
                        overwrite=body.export.overwrite,
                    )
                )
            except Exception as exc:
                metadata_error = f"Downloaded data was saved, but metadata saving failed: {exc}"

        finally:
            state.download_lock.release()

        try:
            file_preview = read_output_preview(result.path, result.output_format, base_dir)
        except CoreError as exc:
            file_preview = {"text": str(exc), "table": None, "size_bytes": result.size_bytes, "truncated": False}

        return {
            **preview_payload(filter_config, query_options, prepared),
            "status_code": response.status_code,
            "elapsed_seconds": response.elapsed_seconds,
            "file": {
                "path": str(result.path),
                "filename": result.filename,
                "output_format": result.output_format,
                "size_bytes": result.size_bytes,
                "record_count": result.record_count,
            },
            "preview": file_preview,
            "metadata_file": metadata_file,
            "metadata_error": metadata_error,
        }

    # -------------------------------------------------------------------------
    # History (local files only)
    # -------------------------------------------------------------------------

    @app.get("/api/history")
    def history() -> dict[str, Any]:
        listing = list_download_history(base_dir)
        return {"entries": listing.entries, "errors": listing.errors}

    @app.get("/api/history/preview")
    def history_preview(meta_file: str) -> dict[str, Any]:
        meta_path = Path(meta_file)
        resolved = meta_path.resolve()
        base = base_dir.resolve()

        if base not in resolved.parents or not resolved.name.endswith("_meta.json"):
            raise fail(400, "Metadata file must be inside the download directory.")

        try:
            data = read_metadata_file(resolved)
        except MetadataError as exc:
            raise fail(404, str(exc)) from exc

        try:
            return read_output_preview(str(data.get("output_file") or ""), str(data.get("output_format") or ""), base_dir)
        except CoreError as exc:
            raise fail(404, str(exc)) from exc

    return app

# =============================================================================
# Main entry point
# =============================================================================

def main() -> int:
    """
    Serve the GUI on 127.0.0.1:8765 and open it in the browser.
    """
    import uvicorn

    print(f"[*] Space-Track Data Downloader GUI on {APP_URL}")
    print("[*] Bound to 127.0.0.1 only. Press Ctrl+C to stop.")

    threading.Timer(1.0, webbrowser.open, args=(APP_URL,)).start()
    uvicorn.run(create_app(), host=HOST, port=PORT, log_level="info")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
