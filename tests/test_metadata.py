# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_metadata.py
# PATH:         space-track-data-downloader/tests/test_metadata.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for metadata.py: sidecar naming, metadata construction,
#               notes, JSON write/read round trips, and header handling.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import json
from pathlib import Path
import pytest
import metadata as md
from exporters import ExportResult, export_response
from metadata import MetadataError
from query_builder import summarize_query

# =============================================================================
# Helpers
# =============================================================================

def make_export(tmp_path: Path, fmt: str = "json", record_count: int | None = 2) -> ExportResult:
    path = tmp_path / f"spacetrack_gp_20261015_120000.{fmt}"
    path.write_text("[]\n")

    return ExportResult(
        path=path,
        filename=path.name,
        output_format=fmt,
        size_bytes=path.stat().st_size,
        record_count=record_count,
        preview="[]",
    )

def gp_summary(**overrides) -> dict:
    kwargs = dict(dataset_key="gp", filters={"OBJECT_TYPE": "DEBRIS"}, output_format="json")
    kwargs.update(overrides)
    return summarize_query(**kwargs)

# =============================================================================
# Paths
# =============================================================================

@pytest.mark.parametrize(
    "output, expected",
    [
        ("downloads/spacetrack_gp_1.json", "downloads/spacetrack_gp_1_meta.json"),
        ("out/x.tle", "out/x_meta.json"),
        ("report.zip", "report_meta.json"),
    ],
)
def test_metadata_path_for_output(output, expected) -> None:
    assert md.metadata_path_for_output(output) == Path(expected)

def test_metadata_avoid_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "a_meta.json"
    target.write_text("{}")
    assert md.avoid_overwrite(target) == tmp_path / "a_meta_1.json"

# =============================================================================
# Serialization
# =============================================================================

def test_to_jsonable_converts_nested_values(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    value = {
        "path": tmp_path / "x",
        "when": datetime(2026, 10, 15, tzinfo=timezone.utc),
        "items": (1, [Path("a")]),
        3: "int key",
    }

    assert md.to_jsonable(value) == {
        "path": str(tmp_path / "x"),
        "when": "2026-10-15T00:00:00+00:00",
        "items": [1, ["a"]],
        "3": "int key",
    }

# =============================================================================
# Notes
# =============================================================================

def test_build_notes_tle_and_ignored_metadata() -> None:
    notes = md.build_notes(
        output_format="tle",
        estimated_record_count=2,
        metadata_supported=False,
        metadata_requested=True,
    )

    assert any("legacy fixed-width" in note for note in notes)
    assert any("not returned or may be ignored" in note for note in notes)
    assert any("not supported for this dataset/format" in note for note in notes)

def test_build_notes_unknown_count_and_custom() -> None:
    notes = md.build_notes(
        output_format="json",
        estimated_record_count=None,
        metadata_supported=True,
        metadata_requested=False,
        custom_notes=["hello"],
    )

    assert notes[0].startswith("Record count is an estimate")
    assert notes[-1] == "hello"

def test_build_notes_clean_json_has_no_notes() -> None:
    assert md.build_notes(
        output_format="json",
        estimated_record_count=5,
        metadata_supported=True,
        metadata_requested=True,
    ) == []

# =============================================================================
# create_download_metadata
# =============================================================================

def test_create_download_metadata_maps_fields(tmp_path: Path) -> None:
    export = make_export(tmp_path)
    summary = gp_summary(limit=10, offset=5, predicates=["NORAD_CAT_ID"], favorites="Geosynchronous")

    meta = md.create_download_metadata(
        query_summary=summary,
        export_result=export,
        response_status_code=200,
        response_elapsed_seconds=1.5,
        response_headers={"Content-Type": "application/json"},
    )

    assert meta.source == "space-track.org"
    assert meta.dataset_key == "gp"
    assert meta.dataset_label == "Latest ELSET / GP data"
    assert meta.controller == "basicspacedata"
    assert meta.api_class == "gp"
    assert meta.output_format == "json"
    assert meta.query_url == summary["url"]
    assert meta.relative_query_path == summary["relative_path"]
    assert meta.filters == {"OBJECT_TYPE": "DEBRIS"}
    assert meta.predicates == ["NORAD_CAT_ID"]
    assert meta.orderby == "NORAD_CAT_ID"
    assert (meta.limit, meta.offset) == (10, 5)
    assert meta.favorites == "Geosynchronous"
    assert meta.output_file == str(export.path)
    assert meta.output_filename == export.filename
    assert meta.output_size_bytes == export.size_bytes
    assert meta.estimated_record_count == 2
    assert meta.response_status_code == 200
    assert meta.response_elapsed_seconds == 1.5
    assert meta.response_headers == {"Content-Type": "application/json"}
    assert meta.notes == []

def test_create_download_metadata_runtime_fields(tmp_path: Path) -> None:
    meta = md.create_download_metadata(query_summary=gp_summary(), export_result=make_export(tmp_path))

    assert meta.runtime.tool_name == md.TOOL_NAME
    assert meta.runtime.tool_version == md.TOOL_VERSION
    assert meta.runtime.username == "tester"
    assert meta.response_headers is None

def test_create_download_metadata_unknown_dataset_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        md.create_download_metadata(
            query_summary={"dataset_key": "nope"},
            export_result=make_export(tmp_path),
        )

# =============================================================================
# Write / read round trip
# =============================================================================

def test_write_and_read_metadata_round_trip(tmp_path: Path) -> None:
    meta = md.create_download_metadata(query_summary=gp_summary(), export_result=make_export(tmp_path))
    written = md.write_metadata_file(meta, tmp_path / "sub" / "m_meta.json")

    data = md.read_metadata_file(written)

    assert data["dataset_key"] == "gp"
    assert data["filters"] == {"OBJECT_TYPE": "DEBRIS"}
    assert data["runtime"]["username"] == "tester"
    assert written.read_text(encoding="utf-8").endswith("}\n")

def test_write_metadata_file_avoids_overwrite(tmp_path: Path) -> None:
    meta = md.create_download_metadata(query_summary=gp_summary(), export_result=make_export(tmp_path))
    target = tmp_path / "m_meta.json"

    first = md.write_metadata_file(meta, target)
    second = md.write_metadata_file(meta, target)
    third = md.write_metadata_file(meta, target, overwrite=True)

    assert (first, second, third) == (target, tmp_path / "m_meta_1.json", target)

def test_write_metadata_file_with_unusable_parent_raises_metadata_write_error(tmp_path: Path) -> None:
    meta = md.create_download_metadata(query_summary=gp_summary(), export_result=make_export(tmp_path))
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")

    with pytest.raises(md.MetadataWriteError):
        md.write_metadata_file(meta, blocker / "m_meta.json")

def test_read_metadata_file_errors(tmp_path: Path) -> None:
    with pytest.raises(MetadataError, match="Failed to read"):
        md.read_metadata_file(tmp_path / "missing.json")

    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(MetadataError, match="not valid JSON"):
        md.read_metadata_file(bad)

    array = tmp_path / "array.json"
    array.write_text("[1, 2]")
    with pytest.raises(MetadataError, match="does not contain a JSON object"):
        md.read_metadata_file(array)

def test_save_metadata_for_export_writes_sidecar(tmp_path: Path, capsys) -> None:
    export = export_response("[]", "gp", "json", download_dir=tmp_path, custom_name="data", print_preview=False)

    path = md.save_metadata_for_export(
        query_summary=gp_summary(),
        export_result=export,
        response_status_code=200,
    )

    assert path == tmp_path / "data_meta.json"
    assert md.read_metadata_file(path)["output_filename"] == "data.json"

    out = capsys.readouterr().out
    assert "METADATA SAVED" in out
    assert "Record count  : 0" in out

def test_print_metadata_file_summary(tmp_path: Path, capsys) -> None:
    meta = md.create_download_metadata(query_summary=gp_summary(), export_result=make_export(tmp_path))
    path = md.write_metadata_file(meta, tmp_path / "m_meta.json")

    md.print_metadata_file_summary(path)
    out = capsys.readouterr().out

    assert "METADATA SUMMARY" in out
    assert "Dataset       : Latest ELSET / GP data" in out
    assert f"Query path    : {meta.relative_query_path}" in out

def test_self_test_writes_into_cwd_downloads(tmp_path: Path) -> None:
    md._self_test()

    assert (tmp_path / "downloads" / "metadata_self_test.json").is_file()
    assert (tmp_path / "downloads" / "metadata_self_test_meta.json").is_file()

# =============================================================================
# Sensitive headers
# =============================================================================

def test_metadata_file_does_not_store_set_cookie(tmp_path: Path) -> None:
    export = make_export(tmp_path)
    headers = {
        "Content-Type": "application/json",
        "Set-Cookie": "chocolatechip=SECRET_SESSION_TOKEN; Max-Age=7200; path=/; HttpOnly",
    }

    path = md.save_metadata_for_export(
        query_summary=gp_summary(),
        export_result=export,
        response_headers=headers,
        print_summary=False,
    )

    text = path.read_text(encoding="utf-8")
    stored_header_names = {name.lower() for name in (json.loads(text)["response_headers"] or {})}

    assert "set-cookie" not in stored_header_names
    assert "SECRET_SESSION_TOKEN" not in text
