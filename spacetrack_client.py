"""
spacetrack_client.py

HTTP client for Space-Track.org.

This module handles:

- Reading credentials from environment variables
- Prompting for credentials when environment variables are missing
- Logging in through /ajaxauth/login
- Checking the current session through /app/data/whoami
- Logging out through /ajaxauth/logout
- Sending GET requests to Space-Track query URLs
- Downloading text or binary responses
- Basic retry handling for temporary network/server failures

This module should not contain interactive dataset menus. It is only the
Space-Track connection/session layer.
"""

from __future__ import annotations

import getpass
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


BASE_URL = "https://www.space-track.org"
LOGIN_ENDPOINT = f"{BASE_URL}/ajaxauth/login"
LOGOUT_ENDPOINT = f"{BASE_URL}/ajaxauth/logout"
WHOAMI_ENDPOINT = f"{BASE_URL}/app/data/whoami"

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_DOWNLOAD_TIMEOUT_SECONDS = 300
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 5.0

ENV_USERNAME_KEYS = (
    "SPACETRACK_USER",
    "SPACETRACK_USERNAME",
    "SPACE_TRACK_USER",
    "SPACE_TRACK_USERNAME",
)

ENV_PASSWORD_KEYS = (
    "SPACETRACK_PASS",
    "SPACETRACK_PASSWORD",
    "SPACE_TRACK_PASS",
    "SPACE_TRACK_PASSWORD",
)


# =============================================================================
# Exceptions
# =============================================================================

class SpaceTrackClientError(Exception):
    """
    Base exception for Space-Track client errors.
    """


class SpaceTrackAuthenticationError(SpaceTrackClientError):
    """
    Raised when authentication fails.
    """


class SpaceTrackRequestError(SpaceTrackClientError):
    """
    Raised when a request fails after retries.
    """


class SpaceTrackConfigurationError(SpaceTrackClientError):
    """
    Raised when client configuration is invalid.
    """


# =============================================================================
# Data containers
# =============================================================================

@dataclass(frozen=True)
class SpaceTrackCredentials:
    """
    Space-Track login credentials.

    Attributes:
        username:
            Space-Track username or email address.

        password:
            Space-Track password.
    """

    username: str
    password: str


@dataclass
class SpaceTrackResponse:
    """
    Simplified response object returned by SpaceTrackClient methods.

    Attributes:
        url:
            Final request URL.

        status_code:
            HTTP status code.

        text:
            Response body decoded as text.

        content:
            Raw response bytes.

        headers:
            Response headers.

        elapsed_seconds:
            Request elapsed time in seconds.
    """

    url: str
    status_code: int
    text: str
    content: bytes
    headers: dict[str, str]
    elapsed_seconds: float

    def json(self) -> Any:
        """
        Parse response text as JSON.
        """
        return json.loads(self.text)


@dataclass
class WhoAmI:
    """
    Parsed Space-Track whoami response.

    Attributes:
        logged_in:
            Whether the session is authenticated.

        identity:
            Authenticated account identity, if available.

        session_expiration:
            Session expiration timestamp string, if available.

        raw:
            Raw parsed JSON response.
    """

    logged_in: bool
    identity: str | None
    session_expiration: str | None
    raw: dict[str, Any]


# =============================================================================
# Credential helpers
# =============================================================================

def _first_env_value(keys: tuple[str, ...]) -> str | None:
    """
    Return the first non-empty environment variable value from a list of keys.
    """
    for key in keys:
        value = os.environ.get(key)

        if value is not None and value.strip() != "":
            return value.strip()

    return None


def load_credentials_from_environment() -> SpaceTrackCredentials | None:
    """
    Load Space-Track credentials from environment variables.

    Supported username variables:
        SPACETRACK_USER
        SPACETRACK_USERNAME
        SPACE_TRACK_USER
        SPACE_TRACK_USERNAME

    Supported password variables:
        SPACETRACK_PASS
        SPACETRACK_PASSWORD
        SPACE_TRACK_PASS
        SPACE_TRACK_PASSWORD

    Returns:
        SpaceTrackCredentials if both username and password are found,
        otherwise None.
    """
    username = _first_env_value(ENV_USERNAME_KEYS)
    password = _first_env_value(ENV_PASSWORD_KEYS)

    if username and password:
        return SpaceTrackCredentials(username=username, password=password)

    return None


def prompt_for_credentials(
    existing_username: str | None = None,
) -> SpaceTrackCredentials:
    """
    Prompt the user for Space-Track credentials.

    Args:
        existing_username:
            Optional username already known from environment variables.

    Returns:
        SpaceTrackCredentials.
    """
    print("\n" + "=" * 72)
    print("SPACE-TRACK.ORG LOGIN")
    print("=" * 72)

    username = existing_username

    if username:
        print(f"Username: {username}")
    else:
        username = input("Username / email: ").strip()

    password = getpass.getpass("Password: ")

    if not username:
        raise SpaceTrackConfigurationError("Username cannot be empty.")

    if not password:
        raise SpaceTrackConfigurationError("Password cannot be empty.")

    return SpaceTrackCredentials(username=username, password=password)


def get_credentials(
    allow_prompt: bool = True,
) -> SpaceTrackCredentials:
    """
    Get Space-Track credentials from environment variables or prompt.

    Args:
        allow_prompt:
            If True, prompt the user when credentials are not fully available.

    Returns:
        SpaceTrackCredentials.

    Raises:
        SpaceTrackConfigurationError:
            If credentials are missing and prompting is disabled.
    """
    env_credentials = load_credentials_from_environment()

    if env_credentials:
        print("[*] Using Space-Track credentials from environment variables.")
        print(f"[*] Username: {env_credentials.username}")
        return env_credentials

    username = _first_env_value(ENV_USERNAME_KEYS)

    if allow_prompt:
        return prompt_for_credentials(existing_username=username)

    raise SpaceTrackConfigurationError(
        "Space-Track credentials were not found in environment variables."
    )


# =============================================================================
# Utility helpers
# =============================================================================

def utc_now_iso() -> str:
    """
    Return the current UTC time as an ISO-8601 string.
    """
    return datetime.now(timezone.utc).isoformat()


def is_space_track_url(url: str) -> bool:
    """
    Return True if a URL belongs to www.space-track.org.
    """
    parsed = urlparse(url)

    return parsed.scheme in {"http", "https"} and parsed.netloc.endswith(
        "space-track.org"
    )


def ensure_space_track_url(url: str) -> None:
    """
    Validate that a URL belongs to Space-Track.

    This prevents accidental requests to unexpected external hosts.
    """
    if not is_space_track_url(url):
        raise SpaceTrackConfigurationError(
            f"Refusing to request non-Space-Track URL: {url}"
        )


def looks_like_login_failure(response_text: str) -> bool:
    """
    Heuristic check for login failure.

    Space-Track login responses can vary. This function catches common failure
    indicators while avoiding reliance on a single exact response.
    """
    text = response_text.lower()

    failure_markers = (
        "login failed",
        "failed",
        "invalid",
        "incorrect",
        "unauthorized",
        "forbidden",
    )

    return any(marker in text for marker in failure_markers)


def response_preview(text: str, max_chars: int = 500) -> str:
    """
    Return a short response preview for error messages.
    """
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "..."


def response_to_spacetrack_response(
    response: requests.Response,
    elapsed_seconds: float,
) -> SpaceTrackResponse:
    """
    Convert requests.Response to SpaceTrackResponse.
    """
    return SpaceTrackResponse(
        url=response.url,
        status_code=response.status_code,
        text=response.text,
        content=response.content,
        headers=dict(response.headers),
        elapsed_seconds=elapsed_seconds,
    )


def is_retryable_status(status_code: int) -> bool:
    """
    Return True if an HTTP status code should usually be retried.
    """
    return status_code in {
        408,
        409,
        425,
        429,
        500,
        502,
        503,
        504,
    }


def sleep_before_retry(
    attempt: int,
    retry_delay_seconds: float,
) -> None:
    """
    Sleep before retrying a failed request.
    """
    delay = retry_delay_seconds * attempt
    print(f"[*] Retrying in {delay:.1f} seconds...")
    time.sleep(delay)


# =============================================================================
# Main client
# =============================================================================

class SpaceTrackClient:
    """
    Space-Track HTTP client.

    Example:
        from spacetrack_client import SpaceTrackClient, get_credentials

        credentials = get_credentials()
        client = SpaceTrackClient()
        client.login(credentials)
        response = client.get("https://www.space-track.org/basicspacedata/query/class/boxscore/format/json")
        print(response.text)
        client.logout()
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        download_timeout_seconds: int = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
        retries: int = DEFAULT_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        user_agent: str = "Space-Track-Data-Downloader/1.0",
    ) -> None:
        """
        Initialize the client.

        Args:
            base_url:
                Space-Track base URL.

            timeout_seconds:
                Default timeout for normal requests.

            download_timeout_seconds:
                Timeout for large downloads.

            retries:
                Number of attempts for retryable requests.

            retry_delay_seconds:
                Base retry delay.

            user_agent:
                User-Agent header sent with requests.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.download_timeout_seconds = download_timeout_seconds
        self.retries = retries
        self.retry_delay_seconds = retry_delay_seconds
        self.user_agent = user_agent

        if self.retries <= 0:
            raise SpaceTrackConfigurationError("retries must be greater than zero.")

        if self.timeout_seconds <= 0:
            raise SpaceTrackConfigurationError(
                "timeout_seconds must be greater than zero."
            )

        if self.download_timeout_seconds <= 0:
            raise SpaceTrackConfigurationError(
                "download_timeout_seconds must be greater than zero."
            )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
            }
        )

        self.logged_in = False
        self.identity: str | None = None
        self.last_login_utc: str | None = None

    def __enter__(self) -> "SpaceTrackClient":
        """
        Enter context manager.
        """
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        """
        Exit context manager and close the session.
        """
        try:
            if self.logged_in:
                self.logout()
        finally:
            self.close()

    def close(self) -> None:
        """
        Close the underlying requests session.
        """
        self.session.close()

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def login(
        self,
        credentials: SpaceTrackCredentials,
    ) -> None:
        """
        Log into Space-Track using ajaxauth/login.

        Args:
            credentials:
                SpaceTrackCredentials.

        Raises:
            SpaceTrackAuthenticationError:
                If login fails.
        """
        print("\n[*] Logging in to Space-Track...")

        data = {
            "identity": credentials.username,
            "password": credentials.password,
        }

        try:
            started = time.monotonic()
            response = self.session.post(
                f"{self.base_url}/ajaxauth/login",
                data=data,
                timeout=self.timeout_seconds,
            )
            elapsed = time.monotonic() - started
        except requests.RequestException as exc:
            raise SpaceTrackAuthenticationError(
                f"Login request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            raise SpaceTrackAuthenticationError(
                "Login failed with HTTP "
                f"{response.status_code}: {response_preview(response.text)}"
            )

        if looks_like_login_failure(response.text):
            raise SpaceTrackAuthenticationError(
                "Login appears to have failed. Response preview: "
                f"{response_preview(response.text)}"
            )

        self.logged_in = True
        self.identity = credentials.username
        self.last_login_utc = utc_now_iso()

        print(f"[+] Logged in as {credentials.username}.")
        print(f"[*] Login request completed in {elapsed:.2f} seconds.")

    def login_from_environment_or_prompt(
        self,
        allow_prompt: bool = True,
    ) -> None:
        """
        Load credentials from environment variables or prompt, then log in.
        """
        credentials = get_credentials(allow_prompt=allow_prompt)
        self.login(credentials)

    def whoami(self) -> WhoAmI:
        """
        Check the current Space-Track session.

        The whoami endpoint also extends the cookie lifetime when authenticated.

        Returns:
            WhoAmI object.
        """
        url = f"{self.base_url}/app/data/whoami"

        response = self.get(url, timeout_seconds=self.timeout_seconds)

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise SpaceTrackRequestError(
                "Could not parse whoami response as JSON. "
                f"Response preview: {response_preview(response.text)}"
            ) from exc

        if not isinstance(data, dict):
            raise SpaceTrackRequestError(
                "Unexpected whoami response. Expected a JSON object."
            )

        logged_in = bool(data.get("logged_in"))
        identity = data.get("identity")
        session_expiration = data.get("session_expiration")

        self.logged_in = logged_in

        if isinstance(identity, str):
            self.identity = identity
        elif not logged_in:
            self.identity = None

        return WhoAmI(
            logged_in=logged_in,
            identity=identity if isinstance(identity, str) else None,
            session_expiration=(
                session_expiration if isinstance(session_expiration, str) else None
            ),
            raw=data,
        )

    def ensure_logged_in(self) -> None:
        """
        Verify that the current session is logged in.

        Raises:
            SpaceTrackAuthenticationError:
                If the session is not logged in.
        """
        info = self.whoami()

        if not info.logged_in:
            raise SpaceTrackAuthenticationError(
                "The current Space-Track session is not authenticated."
            )

    def logout(self) -> None:
        """
        Log out from Space-Track.
        """
        print("[*] Logging out of Space-Track...")

        try:
            response = self.session.get(
                f"{self.base_url}/ajaxauth/logout",
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[!] Logout request failed: {exc}")
        finally:
            self.logged_in = False
            self.identity = None
            print("[+] Logged out.")

    # -------------------------------------------------------------------------
    # Requests
    # -------------------------------------------------------------------------

    def request(
        self,
        method: str,
        url: str,
        *,
        timeout_seconds: int | None = None,
        stream: bool = False,
        allow_non_space_track_url: bool = False,
        **kwargs: Any,
    ) -> SpaceTrackResponse:
        """
        Send an HTTP request with retry handling.

        Args:
            method:
                HTTP method, usually "GET" or "POST".

            url:
                Full request URL.

            timeout_seconds:
                Optional timeout override.

            stream:
                Whether to stream the response.

            allow_non_space_track_url:
                If False, requests are limited to space-track.org URLs.

            **kwargs:
                Additional arguments forwarded to requests.Session.request.

        Returns:
            SpaceTrackResponse.

        Raises:
            SpaceTrackRequestError:
                If the request fails after all retries.
        """
        if not allow_non_space_track_url:
            ensure_space_track_url(url)

        method_upper = method.upper()
        timeout = timeout_seconds or self.timeout_seconds

        last_exception: Exception | None = None
        last_response: requests.Response | None = None
        last_elapsed = 0.0

        for attempt in range(1, self.retries + 1):
            try:
                started = time.monotonic()
                response = self.session.request(
                    method=method_upper,
                    url=url,
                    timeout=timeout,
                    stream=stream,
                    **kwargs,
                )
                elapsed = time.monotonic() - started

                last_response = response
                last_elapsed = elapsed

                if response.status_code == 401:
                    self.logged_in = False
                    raise SpaceTrackAuthenticationError(
                        "Space-Track returned HTTP 401 Unauthorized. "
                        "Your session may have expired or credentials may be invalid."
                    )

                if response.status_code == 403:
                    raise SpaceTrackAuthenticationError(
                        "Space-Track returned HTTP 403 Forbidden. "
                        "Your account may not have access to this resource."
                    )

                if response.status_code >= 400:
                    if is_retryable_status(response.status_code) and attempt < self.retries:
                        print(
                            f"[!] HTTP {response.status_code} on attempt "
                            f"{attempt}/{self.retries}."
                        )
                        print(
                            f"[!] Response preview: "
                            f"{response_preview(response.text)}"
                        )
                        sleep_before_retry(attempt, self.retry_delay_seconds)
                        continue

                    raise SpaceTrackRequestError(
                        f"Request failed with HTTP {response.status_code}. "
                        f"URL: {url}. Response preview: "
                        f"{response_preview(response.text)}"
                    )

                return response_to_spacetrack_response(
                    response=response,
                    elapsed_seconds=elapsed,
                )

            except SpaceTrackAuthenticationError:
                raise

            except requests.Timeout as exc:
                last_exception = exc
                print(
                    f"[!] Timeout on attempt {attempt}/{self.retries}: {exc}"
                )

                if attempt < self.retries:
                    sleep_before_retry(attempt, self.retry_delay_seconds)
                    continue

            except requests.ConnectionError as exc:
                last_exception = exc
                print(
                    f"[!] Connection error on attempt {attempt}/{self.retries}: {exc}"
                )

                if attempt < self.retries:
                    sleep_before_retry(attempt, self.retry_delay_seconds)
                    continue

            except requests.RequestException as exc:
                last_exception = exc
                print(
                    f"[!] Request error on attempt {attempt}/{self.retries}: {exc}"
                )

                if attempt < self.retries:
                    sleep_before_retry(attempt, self.retry_delay_seconds)
                    continue

        if last_response is not None:
            raise SpaceTrackRequestError(
                f"Request failed after {self.retries} attempts. "
                f"Last HTTP status: {last_response.status_code}. "
                f"URL: {url}. Response preview: "
                f"{response_preview(last_response.text)}"
            )

        raise SpaceTrackRequestError(
            f"Request failed after {self.retries} attempts. "
            f"URL: {url}. Last error: {last_exception}"
        )

    def get(
        self,
        url: str,
        *,
        timeout_seconds: int | None = None,
        stream: bool = False,
        allow_non_space_track_url: bool = False,
        **kwargs: Any,
    ) -> SpaceTrackResponse:
        """
        Send a GET request.
        """
        return self.request(
            "GET",
            url,
            timeout_seconds=timeout_seconds,
            stream=stream,
            allow_non_space_track_url=allow_non_space_track_url,
            **kwargs,
        )

    def post(
        self,
        url: str,
        *,
        timeout_seconds: int | None = None,
        stream: bool = False,
        allow_non_space_track_url: bool = False,
        **kwargs: Any,
    ) -> SpaceTrackResponse:
        """
        Send a POST request.
        """
        return self.request(
            "POST",
            url,
            timeout_seconds=timeout_seconds,
            stream=stream,
            allow_non_space_track_url=allow_non_space_track_url,
            **kwargs,
        )

    def download_text(
        self,
        url: str,
        *,
        timeout_seconds: int | None = None,
    ) -> str:
        """
        Download a text response from Space-Track.
        """
        response = self.get(
            url,
            timeout_seconds=timeout_seconds or self.download_timeout_seconds,
        )

        return response.text

    def download_bytes(
        self,
        url: str,
        *,
        timeout_seconds: int | None = None,
    ) -> bytes:
        """
        Download a binary response from Space-Track.
        """
        response = self.get(
            url,
            timeout_seconds=timeout_seconds or self.download_timeout_seconds,
        )

        return response.content

    def download_to_file(
        self,
        url: str,
        output_path: str | Path,
        *,
        timeout_seconds: int | None = None,
        chunk_size: int = 1024 * 1024,
    ) -> Path:
        """
        Stream a Space-Track response directly to a file.

        This is mainly useful for public files and large downloads.

        Args:
            url:
                Full Space-Track URL.

            output_path:
                Destination path.

            timeout_seconds:
                Optional timeout override.

            chunk_size:
                Chunk size in bytes.

        Returns:
            Path to the written file.
        """
        ensure_space_track_url(url)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        timeout = timeout_seconds or self.download_timeout_seconds

        last_exception: Exception | None = None

        for attempt in range(1, self.retries + 1):
            try:
                started = time.monotonic()

                with self.session.get(
                    url,
                    timeout=timeout,
                    stream=True,
                ) as response:
                    if response.status_code == 401:
                        self.logged_in = False
                        raise SpaceTrackAuthenticationError(
                            "Space-Track returned HTTP 401 Unauthorized."
                        )

                    if response.status_code == 403:
                        raise SpaceTrackAuthenticationError(
                            "Space-Track returned HTTP 403 Forbidden."
                        )

                    if response.status_code >= 400:
                        if (
                            is_retryable_status(response.status_code)
                            and attempt < self.retries
                        ):
                            print(
                                f"[!] HTTP {response.status_code} on attempt "
                                f"{attempt}/{self.retries}."
                            )
                            sleep_before_retry(attempt, self.retry_delay_seconds)
                            continue

                        raise SpaceTrackRequestError(
                            f"Download failed with HTTP {response.status_code}. "
                            f"URL: {url}. Response preview: "
                            f"{response_preview(response.text)}"
                        )

                    with output.open("wb") as file_obj:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                file_obj.write(chunk)

                elapsed = time.monotonic() - started
                print(f"[+] Downloaded file to {output} in {elapsed:.2f} seconds.")

                return output

            except SpaceTrackAuthenticationError:
                raise

            except requests.Timeout as exc:
                last_exception = exc
                print(
                    f"[!] Timeout on download attempt {attempt}/{self.retries}: {exc}"
                )

                if attempt < self.retries:
                    sleep_before_retry(attempt, self.retry_delay_seconds)
                    continue

            except requests.ConnectionError as exc:
                last_exception = exc
                print(
                    f"[!] Connection error on download attempt "
                    f"{attempt}/{self.retries}: {exc}"
                )

                if attempt < self.retries:
                    sleep_before_retry(attempt, self.retry_delay_seconds)
                    continue

            except requests.RequestException as exc:
                last_exception = exc
                print(
                    f"[!] Request error on download attempt "
                    f"{attempt}/{self.retries}: {exc}"
                )

                if attempt < self.retries:
                    sleep_before_retry(attempt, self.retry_delay_seconds)
                    continue

        raise SpaceTrackRequestError(
            f"Download failed after {self.retries} attempts. "
            f"URL: {url}. Last error: {last_exception}"
        )

    # -------------------------------------------------------------------------
    # Convenience methods
    # -------------------------------------------------------------------------

    def get_json(
        self,
        url: str,
        *,
        timeout_seconds: int | None = None,
    ) -> Any:
        """
        Download and parse JSON from Space-Track.
        """
        response = self.get(
            url,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
        )

        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise SpaceTrackRequestError(
                "Could not parse response as JSON. "
                f"Response preview: {response_preview(response.text)}"
            ) from exc

    def save_cookies(
        self,
        path: str | Path,
    ) -> Path:
        """
        Save current cookies to a simple JSON file.

        This is not required for normal use, but can help debugging.
        """
        cookie_path = Path(path)
        cookie_path.parent.mkdir(parents=True, exist_ok=True)

        cookies = []

        for cookie in self.session.cookies:
            cookies.append(
                {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "expires": cookie.expires,
                    "secure": cookie.secure,
                }
            )

        cookie_path.write_text(
            json.dumps(cookies, indent=2),
            encoding="utf-8",
        )

        return cookie_path

    def print_session_status(self) -> None:
        """
        Print current session status using whoami.
        """
        try:
            info = self.whoami()
        except SpaceTrackClientError as exc:
            print(f"[!] Could not check session status: {exc}")
            return

        print("\n" + "=" * 72)
        print("SPACE-TRACK SESSION STATUS")
        print("=" * 72)
        print(f"Logged in          : {info.logged_in}")
        print(f"Identity           : {info.identity}")
        print(f"Session expiration : {info.session_expiration}")
        print("=" * 72)


# =============================================================================
# Convenience factory
# =============================================================================

def create_logged_in_client(
    *,
    allow_prompt: bool = True,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    download_timeout_seconds: int = DEFAULT_DOWNLOAD_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> SpaceTrackClient:
    """
    Create a SpaceTrackClient and log in.

    Returns:
        Authenticated SpaceTrackClient.

    Note:
        The caller is responsible for calling client.logout() and client.close(),
        or using the client in a context manager.
    """
    client = SpaceTrackClient(
        timeout_seconds=timeout_seconds,
        download_timeout_seconds=download_timeout_seconds,
        retries=retries,
        retry_delay_seconds=retry_delay_seconds,
    )

    try:
        client.login_from_environment_or_prompt(allow_prompt=allow_prompt)
    except Exception:
        client.close()
        raise

    return client


# =============================================================================
# Self-test
# =============================================================================

def _self_test() -> None:
    """
    Minimal manual self-test.

    This logs in and calls whoami. It requires valid Space-Track credentials.
    """
    client = SpaceTrackClient()

    try:
        client.login_from_environment_or_prompt(allow_prompt=True)
        client.print_session_status()
    finally:
        if client.logged_in:
            client.logout()
        client.close()


if __name__ == "__main__":
    _self_test()