# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         metadata.py 
# PATH:         space-track-data-downloader/metadata.py 
# AUTHOR:       Sooraj Suresh
# DATE:         May 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Creates, serializes, saves, and reads metadata sidecar files for 
#               each Space-Track data download.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import getpass
import json
import platform
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dataset_configs import get_dataset
from exporters import ExportResult

DEFAULT_METADATA_SUFFIX = "_meta"
TOOL_NAME = "Space-Track Data Downloader"
TOOL_VERSION = "1.0.0"

# Headers that carry session credentials and must never be written to disk.
SENSITIVE_HEADER_NAMES = frozenset({"set-cookie", "cookie"})

# =============================================================================
# Exceptions
# =============================================================================

class MetadataError(Exception):
    """
    Base exception for metadata errors.
    """

class MetadataWriteError(MetadataError):
    """
    Raised when writing metadata fails.
    """


# =============================================================================
# Time helpers
# =============================================================================

def utc_now() -> datetime:
    """
    Return the current UTC datetime.
    """
    return datetime.now(timezone.utc)

def utc_now_iso() -> str:
    """
    Return the current UTC time as an ISO-8601 string.
    """
    return utc_now().isoformat()

def utc_now_filename_timestamp() -> str:
    """
    Return the current UTC time as a compact filename-safe timestamp.
    """
    return utc_now().strftime("%Y%m%d_%H%M%S")


# =============================================================================
# Data containers
# =============================================================================

@dataclass
class RuntimeMetadata:
    """
    Runtime information about the environment that created the download.
    """

    tool_name: str = TOOL_NAME
    tool_version: str = TOOL_VERSION
    python_version: str = field(default_factory=lambda: sys.version.replace("\n", " "))
    platform: str = field(default_factory=platform.platform)
    username: str = field(default_factory=getpass.getuser)
    created_utc: str = field(default_factory=utc_now_iso)

@dataclass
class DownloadMetadata:
    """
    Metadata for a Space-Track download.

    Attributes:
        source:
            Data source name.

        created_utc:
            Metadata creation timestamp.

        dataset_key:
            Internal dataset key, such as gp or satcat.

        dataset_label:
            Human-readable dataset label.

        controller:
            Space-Track controller, such as basicspacedata or publicfiles.

        api_class:
            Space-Track API class, such as gp or satcat.

        output_format:
            Output format such as json, csv, xml, kvn, tle, or 3le.

        query_url:
            Full query URL.

        relative_query_path:
            Query path relative to https://www.space-track.org.

        filters:
            Space-Track predicate/value filters used.

        predicates:
            Optional list of returned predicates.

        orderby:
            Optional orderby value.

        limit:
            Optional result limit.

        offset:
            Optional result offset.

        favorites:
            Optional favorites value.

        metadata_requested:
            Whether /metadata/true was requested.

        metadata_supported:
            Whether metadata is meaningful for this format/dataset.

        show_empty:
            Whether /emptyresult/show was requested.

        distinct:
            Whether /distinct/true was requested.

        use_recommended_filters:
            Whether recommended filters were automatically included.

        output_file:
            Saved output file path.

        output_filename:
            Saved output filename.

        output_size_bytes:
            Output file size in bytes.

        estimated_record_count:
            Estimated number of records/objects.

        response_status_code:
            HTTP response status code, if available.

        response_elapsed_seconds:
            HTTP request elapsed time, if available.

        response_headers:
            Optional response headers.

        notes:
            Additional notes.

        runtime:
            Runtime metadata.
    """

    source: str
    created_utc: str
    dataset_key: str
    dataset_label: str
    controller: str
    api_class: str
    output_format: str
    query_url: str
    relative_query_path: str | None
    filters: dict[str, str]
    predicates: list[str] | None
    orderby: str | None
    limit: int | None
    offset: int | None
    favorites: str | None
    metadata_requested: bool
    metadata_supported: bool
    show_empty: bool
    distinct: bool
    use_recommended_filters: bool
    output_file: str
    output_filename: str
    output_size_bytes: int
    estimated_record_count: int | None
    response_status_code: int | None
    response_elapsed_seconds: float | None
    response_headers: dict[str, str] | None
    notes: list[str]
    runtime: RuntimeMetadata

# =============================================================================
# Path helpers
# =============================================================================

def metadata_path_for_output(
    output_path: str | Path,
    *,
    suffix: str = DEFAULT_METADATA_SUFFIX,
) -> Path:
    """
    Build a metadata path for a saved output file.

    Example:
        downloads/spacetrack_gp_20260528_113000.json
        -> downloads/spacetrack_gp_20260528_113000_meta.json
    """
    path = Path(output_path)
    metadata_filename = f"{path.stem}{suffix}.json"

    return path.with_name(metadata_filename)

def avoid_overwrite(path: str | Path) -> Path:
    """
    Return a path that does not overwrite an existing file.

    If the path exists, appends _1, _2, etc. before the extension.
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
# Serialization helpers
# =============================================================================

def to_jsonable(value: Any) -> Any:
    """
    Convert common Python values to JSON-serializable values.
    """
    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]

    return value

def metadata_to_dict(metadata: DownloadMetadata) -> dict[str, Any]:
    """
    Convert DownloadMetadata to a JSON-serializable dictionary.
    """
    data = asdict(metadata)
    return to_jsonable(data)

def metadata_to_json(
    metadata: DownloadMetadata,
    *,
    indent: int = 2,
) -> str:
    """
    Convert DownloadMetadata to a JSON string.
    """
    return json.dumps(
        metadata_to_dict(metadata),
        indent=indent,
        ensure_ascii=False,
    )

# =============================================================================
# Metadata creation
# =============================================================================

def build_notes(
    *,
    output_format: str,
    estimated_record_count: int | None,
    metadata_supported: bool,
    metadata_requested: bool,
    custom_notes: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    """
    Build standard metadata notes.
    """
    notes: list[str] = []

    fmt = output_format.lower().strip()

    if fmt in {"tle", "3le"}:
        notes.append(
            "TLE/3LE are legacy fixed-width formats. JSON, CSV, XML, or KVN "
            "are recommended when expanded catalog identifiers are important."
        )

    if fmt in {"csv", "tle", "3le", "kvn"} and metadata_requested:
        notes.append(
            "Space-Track metadata is not returned or may be ignored for this "
            "output format."
        )

    if metadata_requested and not metadata_supported:
        notes.append(
            "Metadata was requested but is not supported for this dataset/format."
        )

    if estimated_record_count is None:
        notes.append(
            "Record count is an estimate and could not be reliably determined "
            "from this output format."
        )

    if custom_notes:
        notes.extend(str(note) for note in custom_notes)

    return notes

def sanitize_response_headers(
    response_headers: dict[str, str] | None,
) -> dict[str, str] | None:
    """
    Return a copy of response headers without session cookies.

    Header names are matched case-insensitively against SENSITIVE_HEADER_NAMES.
    """
    if not response_headers:
        return None

    return {
        name: value
        for name, value in dict(response_headers).items()
        if name.lower() not in SENSITIVE_HEADER_NAMES
    }

def create_download_metadata(
    *,
    query_summary: dict[str, Any],
    export_result: ExportResult,
    response_status_code: int | None = None,
    response_elapsed_seconds: float | None = None,
    response_headers: dict[str, str] | None = None,
    custom_notes: list[str] | tuple[str, ...] | None = None,
) -> DownloadMetadata:
    """
    Create DownloadMetadata from a query summary and export result.

    Args:
        query_summary:
            Dictionary produced by query_builder.summarize_query().

        export_result:
            ExportResult produced by exporters.export_response().

        response_status_code:
            Optional HTTP status code.

        response_elapsed_seconds:
            Optional request elapsed time.

        response_headers:
            Optional response headers.

        custom_notes:
            Optional user-defined notes.

    Returns:
        DownloadMetadata.
    """
    dataset_key = str(query_summary["dataset_key"])
    dataset = get_dataset(dataset_key)
    output_format = str(query_summary.get("output_format") or export_result.output_format)
    metadata_requested = bool(query_summary.get("metadata_requested", False))
    metadata_supported = bool(query_summary.get("metadata_supported", False))
    notes = build_notes(
        output_format=output_format,
        estimated_record_count=export_result.record_count,
        metadata_supported=metadata_supported,
        metadata_requested=metadata_requested,
        custom_notes=custom_notes,
    )

    return DownloadMetadata(
        source="space-track.org",
        created_utc=utc_now_iso(),
        dataset_key=dataset_key,
        dataset_label=str(query_summary.get("dataset_label") or dataset.label),
        controller=str(query_summary.get("controller") or dataset.controller),
        api_class=str(query_summary.get("api_class") or dataset.api_class),
        output_format=output_format,
        query_url=str(query_summary.get("url") or ""),
        relative_query_path=(
            str(query_summary.get("relative_path"))
            if query_summary.get("relative_path") is not None
            else None
        ),
        filters=dict(query_summary.get("filters") or {}),
        predicates=(
            list(query_summary.get("predicates"))
            if query_summary.get("predicates") is not None
            else None
        ),
        orderby=(
            str(query_summary.get("orderby"))
            if query_summary.get("orderby") is not None
            else None
        ),
        limit=(
            int(query_summary["limit"])
            if query_summary.get("limit") is not None
            else None
        ),
        offset=(
            int(query_summary["offset"])
            if query_summary.get("offset") is not None
            else None
        ),
        favorites=(
            str(query_summary.get("favorites"))
            if query_summary.get("favorites") is not None
            else None
        ),
        metadata_requested=metadata_requested,
        metadata_supported=metadata_supported,
        show_empty=bool(query_summary.get("show_empty", False)),
        distinct=bool(query_summary.get("distinct", False)),
        use_recommended_filters=bool(
            query_summary.get("use_recommended_filters", False)
        ),
        output_file=str(export_result.path),
        output_filename=export_result.filename,
        output_size_bytes=export_result.size_bytes,
        estimated_record_count=export_result.record_count,
        response_status_code=response_status_code,
        response_elapsed_seconds=response_elapsed_seconds,
        response_headers=sanitize_response_headers(response_headers),
        notes=notes,
        runtime=RuntimeMetadata(),
    )


# =============================================================================
# Metadata writing
# =============================================================================

def write_metadata_file(
    metadata: DownloadMetadata,
    metadata_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    """
    Write metadata to a JSON file.

    Args:
        metadata:
            DownloadMetadata object.

        metadata_path:
            Output metadata file path.

        overwrite:
            If False, avoid overwriting existing files.

    Returns:
        Path to the written metadata file.
    """
    path = Path(metadata_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite:
        path = avoid_overwrite(path)

    try:
        path.write_text(
            metadata_to_json(metadata) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise MetadataWriteError(
            f"Failed to write metadata file {path}: {exc}"
        ) from exc

    return path

def save_metadata_for_export(
    *,
    query_summary: dict[str, Any],
    export_result: ExportResult,
    response_status_code: int | None = None,
    response_elapsed_seconds: float | None = None,
    response_headers: dict[str, str] | None = None,
    custom_notes: list[str] | tuple[str, ...] | None = None,
    overwrite: bool = False,
    print_summary: bool = True,
) -> Path:
    """
    Create and save a metadata sidecar file for an exported response.

    Returns:
        Path to the metadata JSON file.
    """
    metadata = create_download_metadata(
        query_summary=query_summary,
        export_result=export_result,
        response_status_code=response_status_code,
        response_elapsed_seconds=response_elapsed_seconds,
        response_headers=response_headers,
        custom_notes=custom_notes,
    )

    path = metadata_path_for_output(export_result.path)

    written_path = write_metadata_file(
        metadata=metadata,
        metadata_path=path,
        overwrite=overwrite,
    )

    if print_summary:
        print_metadata_summary(written_path, metadata)

    return written_path

# =============================================================================
# Metadata reading
# =============================================================================

def read_metadata_file(path: str | Path) -> dict[str, Any]:
    """
    Read a metadata JSON file.

    Returns:
        Parsed metadata dictionary.
    """
    metadata_path = Path(path)

    try:
        text = metadata_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MetadataError(f"Failed to read metadata file {metadata_path}: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MetadataError(
            f"Metadata file is not valid JSON: {metadata_path}"
        ) from exc

    if not isinstance(data, dict):
        raise MetadataError(
            f"Metadata file does not contain a JSON object: {metadata_path}"
        )

    return data


# =============================================================================
# Terminal summary helpers
# =============================================================================

def print_metadata_summary(
    metadata_path: str | Path,
    metadata: DownloadMetadata | None = None,
) -> None:
    """
    Print a short metadata summary.
    """
    path = Path(metadata_path)

    print("\n" + "=" * 72)
    print("METADATA SAVED")
    print("=" * 72)
    print(f"Metadata file : {path}")

    if metadata is not None:
        print(f"Dataset       : {metadata.dataset_label}")
        print(f"API class     : {metadata.api_class}")
        print(f"Format        : {metadata.output_format}")
        print(f"Output file   : {metadata.output_file}")

        if metadata.estimated_record_count is not None:
            print(f"Record count  : {metadata.estimated_record_count}")
        else:
            print("Record count  : unknown")

    print("=" * 72)

def print_metadata_file_summary(path: str | Path) -> None:
    """
    Read a metadata file and print a short summary.
    """
    data = read_metadata_file(path)

    print("\n" + "=" * 72)
    print("METADATA SUMMARY")
    print("=" * 72)
    print(f"Metadata file : {path}")
    print(f"Dataset       : {data.get('dataset_label')}")
    print(f"API class     : {data.get('api_class')}")
    print(f"Format        : {data.get('output_format')}")
    print(f"Output file   : {data.get('output_file')}")
    print(f"Created UTC   : {data.get('created_utc')}")
    print(f"Query path    : {data.get('relative_query_path')}")
    print("=" * 72)

# =============================================================================
# Self-test
# =============================================================================

def _self_test() -> None:
    """
    Minimal metadata self-test.

    This creates a temporary-looking metadata object. It assumes metadata.py    
    is available and working.
    """
    from exporters import export_json_object

    sample_query_summary = {
        "dataset_key": "gp",
        "dataset_label": "Latest ELSET / GP data",
        "controller": "basicspacedata",
        "api_class": "gp",
        "filters": {
            "OBJECT_TYPE": "DEBRIS",
            "DECAY_DATE": "null-val",
            "EPOCH": ">now-10",
        },
        "output_format": "json",
        "predicates": None,
        "orderby": "NORAD_CAT_ID",
        "limit": None,
        "offset": None,
        "metadata_requested": False,
        "metadata_supported": True,
        "show_empty": False,
        "favorites": None,
        "distinct": False,
        "raw_extra_path": None,
        "publicfiles_download_name": None,
        "use_recommended_filters": False,
        "url": (
            "https://www.space-track.org/basicspacedata/query/class/gp/"
            "OBJECT_TYPE/DEBRIS/DECAY_DATE/null-val/EPOCH/%3Enow-10/"
            "orderby/NORAD_CAT_ID/format/json"
        ),
        "relative_path": (
            "/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS/"
            "DECAY_DATE/null-val/EPOCH/%3Enow-10/orderby/NORAD_CAT_ID/"
            "format/json"
        ),
    }

    export_result = export_json_object(
        [
            {
                "NORAD_CAT_ID": "25544",
                "OBJECT_NAME": "ISS",
            }
        ],
        dataset_key="gp",
        custom_name="metadata_self_test",
        overwrite=True,
        print_preview=False,
    )

    save_metadata_for_export(
        query_summary=sample_query_summary,
        export_result=export_result,
        response_status_code=200,
        response_elapsed_seconds=1.23,
        response_headers={"content-type": "application/json"},
        overwrite=True,
    )


if __name__ == "__main__":
    _self_test()