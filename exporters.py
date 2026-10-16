# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         exporters.py
# PATH:         space-track-data-downloader/exporters.py
# AUTHOR:       Sooraj Suresh
# DATE:         May 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Saves Space-Track API responses to disk, creates output filenames, 
#               estimates record counts, and prints export previews.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dataset_configs import get_file_extension, get_safe_dataset_filename_part

DEFAULT_DOWNLOAD_DIR = Path("downloads")
DEFAULT_FILENAME_PREFIX = "spacetrack"

# =============================================================================
# Exceptions
# =============================================================================

class ExporterError(Exception):
    """
    Base exception for exporter errors.
    """

class UnsupportedExportFormatError(ExporterError):
    """
    Raised when an unsupported output format is requested.
    """

class FileWriteError(ExporterError):
    """
    Raised when writing a file fails.
    """

# =============================================================================
# Data containers
# =============================================================================

@dataclass(frozen=True)
class ExportResult:
    """
    Information about a saved output file.

    Attributes:
        path:
            Path to the saved output file.

        filename:
            Name of the saved output file.

        output_format:
            Output format used for the file.

        size_bytes:
            File size in bytes.

        record_count:
            Estimated number of records or objects in the response.

        preview:
            Short text preview of the saved content.
    """

    path: Path
    filename: str
    output_format: str
    size_bytes: int
    record_count: int | None
    preview: str

# =============================================================================
# Path and filename helpers
# =============================================================================

def utc_timestamp_for_filename() -> str:
    """
    Return a compact UTC timestamp suitable for filenames.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def ensure_download_dir(download_dir: str | Path = DEFAULT_DOWNLOAD_DIR) -> Path:
    """
    Ensure the download directory exists.

    Args:
        download_dir:
            Directory where output files should be saved.

    Returns:
        Path to the directory.
    """
    directory = Path(download_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory

def sanitize_filename_part(value: str) -> str:
    """
    Sanitize a string so it can safely be used as part of a filename.
    Keeps letters, numbers, hyphens, underscores, and dots. Other characters
    are replaced with underscores.
    """
    text = str(value).strip()

    if text == "":
        return "unknown"

    text = text.replace(" ", "_")
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("._-")

    if text == "":
        return "unknown"

    return text.lower()

def build_output_filename(
    dataset_key: str,
    output_format: str,
    *,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
) -> str:
    """
    Build a safe output filename.

    Args:
        dataset_key:
            Dataset key, such as gp, satcat, decay, or cdm_public.

        output_format:
            Output format, such as json, csv, xml, kvn, tle, 3le, html, or raw.

        prefix:
            Filename prefix.

        timestamp:
            Optional timestamp. If omitted, current UTC timestamp is used.

        custom_name:
            Optional custom filename without extension. If provided, it is used
            instead of the default prefix/dataset/timestamp pattern.

    Returns:
        Filename as a string.
    """
    fmt = output_format.lower().strip()
    extension = get_file_extension(fmt)

    if timestamp is None:
        timestamp = utc_timestamp_for_filename()

    if custom_name:
        base_name = sanitize_filename_part(custom_name)
    else:
        safe_prefix = sanitize_filename_part(prefix)
        safe_dataset = sanitize_filename_part(
            get_safe_dataset_filename_part(dataset_key)
        )
        base_name = f"{safe_prefix}_{safe_dataset}_{timestamp}"

    if base_name.endswith(extension):
        return base_name

    return f"{base_name}{extension}"

def build_output_path(
    dataset_key: str,
    output_format: str,
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
) -> Path:
    """
    Build a full output path inside the download directory.
    """
    directory = ensure_download_dir(download_dir)

    filename = build_output_filename(
        dataset_key=dataset_key,
        output_format=output_format,
        prefix=prefix,
        timestamp=timestamp,
        custom_name=custom_name,
    )

    return directory / filename

def avoid_overwrite(path: str | Path) -> Path:
    """
    Return a path that does not overwrite an existing file.

    If the path already exists, appends _1, _2, etc. before the extension.
    """
    candidate = Path(path)

    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent

    counter = 1

    while True:
        new_candidate = parent / f"{stem}_{counter}{suffix}"

        if not new_candidate.exists():
            return new_candidate

        counter += 1

# =============================================================================
# Response normalization helpers
# =============================================================================

def normalize_text_content(content: str | bytes) -> str:
    """
    Normalize text content.

    Args:
        content:
            String or bytes response.

    Returns:
        UTF-8 decoded string.
    """
    if isinstance(content, bytes):
        return content.decode("utf-8", errors="replace")

    return str(content)

def normalize_binary_content(content: str | bytes) -> bytes:
    """
    Normalize binary content.

    Args:
        content:
            String or bytes response.

    Returns:
        Bytes.
    """
    if isinstance(content, bytes):
        return content

    return str(content).encode("utf-8")

def is_probably_binary(output_format: str) -> bool:
    """
    Return True if a format should normally be saved as binary.
    """
    return output_format.lower().strip() in {"raw", "bin", "zip"}

def pretty_json_text(text: str) -> str:
    """
    Pretty-format JSON text when possible.

    If the input is not valid JSON, it is returned unchanged.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text

    return json.dumps(parsed, indent=2, ensure_ascii=False)

def normalize_content_for_export(
    content: str | bytes,
    output_format: str,
    *,
    pretty_json: bool = True,
) -> str | bytes:
    """
    Normalize content before saving based on output format.
    JSON can optionally be pretty-printed.
    Binary/raw formats are returned as bytes.
    """
    fmt = output_format.lower().strip()

    if is_probably_binary(fmt):
        return normalize_binary_content(content)

    text = normalize_text_content(content)

    if fmt == "json" and pretty_json:
        text = pretty_json_text(text)

    return text

# =============================================================================
# Record counting helpers
# =============================================================================

def count_json_records(text: str) -> int | None:
    """
    Count records in JSON text.

    Returns:
        int:
            Number of records if the JSON root is a list or object.

        None:
            If the text is not valid JSON.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, list):
        return len(parsed)

    if isinstance(parsed, dict):
        if "data" in parsed and isinstance(parsed["data"], list):
            return len(parsed["data"])

        if "results" in parsed and isinstance(parsed["results"], list):
            return len(parsed["results"])

        return 1

    return None

def count_csv_records(text: str) -> int | None:
    """
    Count data rows in CSV text.

    Returns:
        Number of rows excluding the header, or None if counting fails.
    """
    stripped = text.strip()

    if not stripped:
        return 0

    try:
        rows = [
            row
            for row in csv.reader(stripped.splitlines())
            if any(cell.strip() for cell in row)
        ]
    except csv.Error:
        return None

    if not rows:
        return 0

    return max(0, len(rows) - 1)

def count_tle_records(text: str) -> int:
    """
    Count TLE records in two-line TLE text.

    This counts pairs of lines where line 1 starts with '1 ' and line 2 starts
    with '2 '.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    count = 0
    i = 0

    while i < len(lines) - 1:
        if lines[i].startswith("1 ") and lines[i + 1].startswith("2 "):
            count += 1
            i += 2
        else:
            i += 1

    return count

def count_3le_records(text: str) -> int:
    """
    Count 3LE records in three-line TLE text.
    This counts groups where the second line starts with '1 ' and the third line
    starts with '2 '.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    count = 0
    i = 0

    while i < len(lines) - 2:
        if lines[i + 1].startswith("1 ") and lines[i + 2].startswith("2 "):
            count += 1
            i += 3
        else:
            i += 1

    return count


def count_xml_records(text: str) -> int | None:
    """
    Estimate XML record count.
    This is intentionally conservative because XML structure may vary by class.
    """
    stripped = text.strip()

    if not stripped:
        return 0

    lower = stripped.lower()

    possible_record_tags = (
        "omm",
        "cdm",
        "record",
        "result",
        "satellite",
        "object",
    )

    # Match whole opening tags only, so <object> does not also count
    # <OBJECT_NAME> or <OBJECT_ID>.
    counts = [
        len(re.findall(rf"<{tag}(?=[\s/>])", lower))
        for tag in possible_record_tags
    ]
    best = max(counts) if counts else 0

    if best > 0:
        return best

    return None

def count_html_rows(text: str) -> int | None:
    """
    Estimate record count in HTML table output by counting table row tags.
    """
    stripped = text.strip()

    if not stripped:
        return 0

    lower = stripped.lower()
    row_count = lower.count("<tr")

    if row_count == 0:
        return None

    return max(0, row_count - 1)

def count_records(
    content: str | bytes,
    output_format: str,
) -> int | None:
    """
    Count records or objects in Space-Track output.
    Returns:
        int or None if no reliable count can be determined.
    """
    fmt = output_format.lower().strip()

    if is_probably_binary(fmt):
        return None

    text = normalize_text_content(content)

    if not text.strip():
        return 0

    if fmt == "json":
        return count_json_records(text)

    if fmt == "csv":
        return count_csv_records(text)

    if fmt == "tle":
        return count_tle_records(text)

    if fmt == "3le":
        return count_3le_records(text)

    if fmt == "xml":
        return count_xml_records(text)

    if fmt == "html":
        return count_html_rows(text)

    if fmt == "kvn":
        return None

    return None

# =============================================================================
# Preview helpers
# =============================================================================

def make_text_preview(
    content: str | bytes,
    output_format: str,
    *,
    max_lines: int = 20,
    max_chars: int = 3000,
) -> str:
    """
    Create a short preview for terminal display.
    """
    fmt = output_format.lower().strip()

    if is_probably_binary(fmt):
        binary = normalize_binary_content(content)
        return f"<binary content: {len(binary)} bytes>"

    text = normalize_text_content(content)

    if not text.strip():
        return "<empty response>"

    lines = text.splitlines()

    if fmt == "json":
        text = pretty_json_text(text)
        lines = text.splitlines()

    preview = "\n".join(lines[:max_lines])

    if len(preview) > max_chars:
        preview = preview[:max_chars] + "\n..."

    if len(lines) > max_lines:
        preview += f"\n... ({len(lines) - max_lines} more lines)"

    return preview

def print_export_preview(
    export_result: ExportResult,
) -> None:
    """
    Print a short summary of an exported file.
    """
    print("\n" + "=" * 72)
    print("EXPORT COMPLETE")
    print("=" * 72)
    print(f"File          : {export_result.path}")
    print(f"Format        : {export_result.output_format}")
    print(f"Size          : {export_result.size_bytes} bytes")

    if export_result.record_count is not None:
        print(f"Record count  : {export_result.record_count}")
    else:
        print("Record count  : unknown")

    print("\nPreview:")
    print("-" * 72)
    print(export_result.preview)
    print("=" * 72)

# =============================================================================
# File writing helpers
# =============================================================================

def write_text_file(
    path: str | Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> Path:
    """
    Write text to a file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.write_text(text, encoding=encoding)
    except OSError as exc:
        raise FileWriteError(f"Failed to write text file {output_path}: {exc}") from exc

    return output_path

def write_binary_file(
    path: str | Path,
    content: bytes,
) -> Path:
    """
    Write bytes to a file.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        output_path.write_bytes(content)
    except OSError as exc:
        raise FileWriteError(
            f"Failed to write binary file {output_path}: {exc}"
        ) from exc

    return output_path

def export_response(
    content: str | bytes,
    dataset_key: str,
    output_format: str,
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
    overwrite: bool = False,
    pretty_json: bool = True,
    print_preview: bool = True,
) -> ExportResult:
    """
    Export a Space-Track response to disk.

    Args:
        content:
            Response body as text or bytes.

        dataset_key:
            Dataset key.

        output_format:
            Output format.

        download_dir:
            Directory where the file should be saved.

        prefix:
            Filename prefix.

        timestamp:
            Optional timestamp for filename.

        custom_name:
            Optional custom filename base.

        overwrite:
            If False, avoid overwriting existing files.

        pretty_json:
            Pretty-print JSON output when possible.

        print_preview:
            Print an export summary and preview.

    Returns:
        ExportResult.
    """
    fmt = output_format.lower().strip()

    path = build_output_path(
        dataset_key=dataset_key,
        output_format=fmt,
        download_dir=download_dir,
        prefix=prefix,
        timestamp=timestamp,
        custom_name=custom_name,
    )

    if not overwrite:
        path = avoid_overwrite(path)

    normalized = normalize_content_for_export(
        content=content,
        output_format=fmt,
        pretty_json=pretty_json,
    )

    if isinstance(normalized, bytes):
        write_binary_file(path, normalized)
        final_content_for_count = normalized
    else:
        if normalized and not normalized.endswith("\n"):
            normalized += "\n"

        write_text_file(path, normalized)
        final_content_for_count = normalized

    size_bytes = path.stat().st_size
    record_count = count_records(final_content_for_count, fmt)
    preview = make_text_preview(final_content_for_count, fmt)

    result = ExportResult(
        path=path,
        filename=path.name,
        output_format=fmt,
        size_bytes=size_bytes,
        record_count=record_count,
        preview=preview,
    )

    if print_preview:
        print_export_preview(result)

    return result

def export_text_response(
    text: str,
    dataset_key: str,
    output_format: str,
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
    overwrite: bool = False,
    pretty_json: bool = True,
    print_preview: bool = True,
) -> ExportResult:
    """
    Export a text response to disk.
    """
    return export_response(
        content=text,
        dataset_key=dataset_key,
        output_format=output_format,
        download_dir=download_dir,
        prefix=prefix,
        timestamp=timestamp,
        custom_name=custom_name,
        overwrite=overwrite,
        pretty_json=pretty_json,
        print_preview=print_preview,
    )

def export_binary_response(
    content: bytes,
    dataset_key: str,
    output_format: str = "raw",
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
    overwrite: bool = False,
    print_preview: bool = True,
) -> ExportResult:
    """
    Export a binary response to disk.
    """
    return export_response(
        content=content,
        dataset_key=dataset_key,
        output_format=output_format,
        download_dir=download_dir,
        prefix=prefix,
        timestamp=timestamp,
        custom_name=custom_name,
        overwrite=overwrite,
        pretty_json=False,
        print_preview=print_preview,
    )

# =============================================================================
# Specialized helpers
# =============================================================================

def export_json_object(
    data: Any,
    dataset_key: str,
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
    overwrite: bool = False,
    print_preview: bool = True,
) -> ExportResult:
    """
    Export a Python object as pretty JSON.
    """
    text = json.dumps(data, indent=2, ensure_ascii=False)

    return export_text_response(
        text=text,
        dataset_key=dataset_key,
        output_format="json",
        download_dir=download_dir,
        prefix=prefix,
        timestamp=timestamp,
        custom_name=custom_name,
        overwrite=overwrite,
        pretty_json=False,
        print_preview=print_preview,
    )

def export_lines(
    lines: list[str] | tuple[str, ...],
    dataset_key: str,
    output_format: str,
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    prefix: str = DEFAULT_FILENAME_PREFIX,
    timestamp: str | None = None,
    custom_name: str | None = None,
    overwrite: bool = False,
    print_preview: bool = True,
) -> ExportResult:
    """
    Export a list of text lines.
    """
    text = "\n".join(lines)

    return export_text_response(
        text=text,
        dataset_key=dataset_key,
        output_format=output_format,
        download_dir=download_dir,
        prefix=prefix,
        timestamp=timestamp,
        custom_name=custom_name,
        overwrite=overwrite,
        pretty_json=False,
        print_preview=print_preview,
    )

def export_public_file_bytes(
    content: bytes,
    original_name: str,
    *,
    download_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
    overwrite: bool = False,
    print_preview: bool = True,
) -> ExportResult:
    """
    Export a public file download using the original file name when possible.
    """
    safe_name = sanitize_filename_part(original_name)

    if not safe_name:
        safe_name = f"public_file_{utc_timestamp_for_filename()}"

    path = ensure_download_dir(download_dir) / safe_name

    if not overwrite:
        path = avoid_overwrite(path)

    write_binary_file(path, content)

    size_bytes = path.stat().st_size
    preview = f"<binary public file: {size_bytes} bytes>"

    result = ExportResult(
        path=path,
        filename=path.name,
        output_format="raw",
        size_bytes=size_bytes,
        record_count=None,
        preview=preview,
    )

    if print_preview:
        print_export_preview(result)

    return result

# =============================================================================
# Self-test
# =============================================================================

def _self_test() -> None:
    """
    Run a simple exporter self-test.
    """
    sample_json = [
        {
            "NORAD_CAT_ID": "25544",
            "OBJECT_NAME": "ISS",
            "EPOCH": "2026-01-01T00:00:00",
        },
        {
            "NORAD_CAT_ID": "43013",
            "OBJECT_NAME": "EXAMPLE",
            "EPOCH": "2026-01-01T00:00:00",
        },
    ]

    export_json_object(
        sample_json,
        dataset_key="gp",
        custom_name="exporter_self_test",
        overwrite=True,
    )


if __name__ == "__main__":
    _self_test()