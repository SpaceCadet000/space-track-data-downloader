# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_exporters.py
# PATH:         space-track-data-downloader/tests/test_exporters.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for exporters.py: filename building, overwrite avoidance,
#               content normalization, record counting, previews, and writes.
#               Every write goes to pytest's tmp_path.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import json
from pathlib import Path
import pytest
import exporters as ex
from exporters import ExportResult, FileWriteError

TS = "20261015_120000"

# =============================================================================
# Filenames and paths
# =============================================================================

@pytest.mark.parametrize(
    "value, expected",
    [
        ("GP History", "gp_history"),
        ("../../etc/passwd", "etc_passwd"),
        ("My File (1).ZIP", "my_file_1_.zip"),
        ("...", "unknown"),
        ("   ", "unknown"),
        ("a!!!b", "a_b"),
    ],
)
def test_sanitize_filename_part(value, expected) -> None:
    assert ex.sanitize_filename_part(value) == expected

@pytest.mark.parametrize(
    "dataset_key, fmt, custom_name, expected",
    [
        ("gp", "json", None, f"spacetrack_gp_{TS}.json"),
        ("gp_history", "3le", None, f"spacetrack_gp_history_{TS}.tle"),
        ("publicfiles_download", "raw", None, f"spacetrack_publicfiles_download_{TS}.bin"),
        ("gp", "JSON", None, f"spacetrack_gp_{TS}.json"),
        ("gp", "json", "My Debris", "my_debris.json"),
        ("gp", "json", "data.json", "data.json"),
        ("gp", "json", "data.csv", "data.csv.json"),
        ("gp", "json", "", f"spacetrack_gp_{TS}.json"),
    ],
)
def test_build_output_filename(dataset_key, fmt, custom_name, expected) -> None:
    assert ex.build_output_filename(
        dataset_key, fmt, timestamp=TS, custom_name=custom_name
    ) == expected

def test_build_output_filename_default_timestamp_shape() -> None:
    name = ex.build_output_filename("gp", "csv")
    stamp = name.removeprefix("spacetrack_gp_").removesuffix(".csv")
    assert len(stamp) == len(TS) and stamp[8] == "_" and stamp.replace("_", "").isdigit()

def test_build_output_path_creates_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "out"
    path = ex.build_output_path("gp", "csv", download_dir=target, timestamp=TS)

    assert target.is_dir()
    assert path == target / f"spacetrack_gp_{TS}.csv"

def test_avoid_overwrite(tmp_path: Path) -> None:
    original = tmp_path / "x.json"
    assert ex.avoid_overwrite(original) == original

    original.write_text("1")
    assert ex.avoid_overwrite(original) == tmp_path / "x_1.json"

    (tmp_path / "x_1.json").write_text("2")
    assert ex.avoid_overwrite(original) == tmp_path / "x_2.json"

# =============================================================================
# Normalization
# =============================================================================

def test_pretty_json_text() -> None:
    assert ex.pretty_json_text('[{"a":1}]') == '[\n  {\n    "a": 1\n  }\n]'
    assert ex.pretty_json_text("not json") == "not json"

def test_normalize_content_for_export() -> None:
    assert ex.normalize_content_for_export('{"a":1}', "json") == '{\n  "a": 1\n}'
    assert ex.normalize_content_for_export('{"a":1}', "json", pretty_json=False) == '{"a":1}'
    assert ex.normalize_content_for_export(b"caf\xc3\xa9", "csv") == "café"
    assert ex.normalize_content_for_export(b"\xff\xfe", "csv") == "��"
    assert ex.normalize_content_for_export("abc", "raw") == b"abc"
    assert ex.normalize_content_for_export(b"\x00\x01", "zip") == b"\x00\x01"

@pytest.mark.parametrize("fmt, expected", [("raw", True), ("BIN", True), ("zip", True), ("json", False)])
def test_is_probably_binary(fmt, expected) -> None:
    assert ex.is_probably_binary(fmt) is expected

# =============================================================================
# Record counting
# =============================================================================

def test_count_json_records(fixture_text) -> None:
    assert ex.count_json_records(fixture_text("gp_sample.json")) == 2
    assert ex.count_json_records('{"request_metadata": {}, "data": [1, 2, 3]}') == 3
    assert ex.count_json_records('{"results": [1]}') == 1
    assert ex.count_json_records('{"single": "object"}') == 1
    assert ex.count_json_records("null") is None
    assert ex.count_json_records("not json") is None

def test_count_csv_records(fixture_text) -> None:
    assert ex.count_csv_records(fixture_text("gp_sample.csv")) == 2
    assert ex.count_csv_records("NORAD_CAT_ID,OBJECT_NAME\n") == 0
    assert ex.count_csv_records("") == 0
    assert ex.count_csv_records('h1,h2\n"multi\nline",x\n') == 1

@pytest.mark.xfail(reason="BUG: count_csv_records counts blank lines as data rows")
def test_count_csv_records_ignores_blank_lines() -> None:
    assert ex.count_csv_records("h\n\nr1\n") == 1

def test_count_tle_records(fixture_text) -> None:
    assert ex.count_tle_records(fixture_text("gp_sample.tle")) == 2
    assert ex.count_tle_records(fixture_text("gp_sample.3le")) == 2
    assert ex.count_tle_records("1 orphan line only\n") == 0

def test_count_3le_records(fixture_text) -> None:
    assert ex.count_3le_records(fixture_text("gp_sample.3le")) == 2
    assert ex.count_3le_records("0 NAME\n1 x\n") == 0

def test_count_xml_records_cdm_and_empty() -> None:
    assert ex.count_xml_records("<cdm></cdm><cdm></cdm>") == 2
    assert ex.count_xml_records("   ") == 0
    assert ex.count_xml_records("<xml><item/></xml>") is None

@pytest.mark.xfail(
    reason="BUG: count_xml_records matches '<object' inside <OBJECT_NAME>/<OBJECT_ID>, "
    "so each OMM record is counted twice"
)
def test_count_xml_records_omm(fixture_text) -> None:
    assert ex.count_xml_records(fixture_text("omm_sample.xml")) == 2

def test_count_html_rows(fixture_text) -> None:
    assert ex.count_html_rows(fixture_text("boxscore_sample.html")) == 3
    assert ex.count_html_rows("<table><tr><th>H</th></tr></table>") == 0
    assert ex.count_html_rows("<p>no table</p>") is None

@pytest.mark.parametrize(
    "content, fmt, expected",
    [
        ("", "json", 0),
        ("   \n", "kvn", 0),
        ("CCSDS_OMM_VERS = 2.0", "kvn", None),
        ("anything", "unknown", None),
        (b"\x00\x01", "raw", None),
        (b'[{"a": 1}]', "json", 1),
    ],
)
def test_count_records_dispatch(content, fmt, expected) -> None:
    assert ex.count_records(content, fmt) == expected

# =============================================================================
# Previews
# =============================================================================

def test_make_text_preview_binary_and_empty() -> None:
    assert ex.make_text_preview(b"12345", "raw") == "<binary content: 5 bytes>"
    assert ex.make_text_preview("  \n", "csv") == "<empty response>"

def test_make_text_preview_truncates_lines() -> None:
    text = "\n".join(f"line {i}" for i in range(25))
    preview = ex.make_text_preview(text, "csv")

    assert preview.startswith("line 0\n")
    assert "line 19" in preview
    assert "line 20" not in preview
    assert preview.endswith("... (5 more lines)")

def test_make_text_preview_truncates_chars() -> None:
    preview = ex.make_text_preview("x" * 50, "csv", max_chars=10)
    assert preview == "x" * 10 + "\n..."

def test_make_text_preview_pretty_prints_json() -> None:
    assert ex.make_text_preview('{"a":1}', "json") == '{\n  "a": 1\n}'

def test_print_export_preview(capsys, tmp_path: Path) -> None:
    result = ExportResult(
        path=tmp_path / "f.json",
        filename="f.json",
        output_format="json",
        size_bytes=10,
        record_count=None,
        preview="PREVIEW-TEXT",
    )

    ex.print_export_preview(result)
    out = capsys.readouterr().out

    assert "EXPORT COMPLETE" in out
    assert "Record count  : unknown" in out
    assert "PREVIEW-TEXT" in out

# =============================================================================
# Low-level writes
# =============================================================================

def test_write_text_and_binary_files(tmp_path: Path) -> None:
    text_path = ex.write_text_file(tmp_path / "a" / "t.txt", "héllo")
    bin_path = ex.write_binary_file(tmp_path / "b" / "b.bin", b"\x00\xff")

    assert text_path.read_text(encoding="utf-8") == "héllo"
    assert bin_path.read_bytes() == b"\x00\xff"

def test_write_text_file_to_directory_raises_file_write_error(tmp_path: Path) -> None:
    with pytest.raises(FileWriteError):
        ex.write_text_file(tmp_path, "x")

def test_write_binary_file_to_directory_raises_file_write_error(tmp_path: Path) -> None:
    with pytest.raises(FileWriteError):
        ex.write_binary_file(tmp_path, b"x")

@pytest.mark.xfail(
    raises=AssertionError,
    reason="BUG: mkdir runs outside the try block, so a parent that is a file "
    "raises a raw OSError instead of FileWriteError",
)
@pytest.mark.parametrize("writer, payload", [(ex.write_text_file, "x"), (ex.write_binary_file, b"x")])
def test_write_with_unusable_parent_raises_file_write_error(tmp_path: Path, writer, payload) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")

    try:
        writer(blocker / "child.txt", payload)
    except FileWriteError:
        return
    except OSError as exc:
        raise AssertionError(f"raw {type(exc).__name__} escaped instead of FileWriteError") from exc

    raise AssertionError("no error raised")

# =============================================================================
# High-level exports
# =============================================================================

def test_export_response_json(tmp_path: Path, fixture_text, capsys) -> None:
    result = ex.export_response(
        fixture_text("gp_sample.json"),
        "gp",
        "json",
        download_dir=tmp_path,
        timestamp=TS,
    )

    assert result.path == tmp_path / f"spacetrack_gp_{TS}.json"
    assert result.filename == result.path.name
    assert result.output_format == "json"
    assert result.record_count == 2
    assert result.size_bytes == result.path.stat().st_size

    written = result.path.read_text(encoding="utf-8")
    assert written.endswith("\n")
    assert json.loads(written)[0]["NORAD_CAT_ID"] == "25544"
    assert '\n  {\n    "NORAD_CAT_ID"' in written

    assert "EXPORT COMPLETE" in capsys.readouterr().out

def test_export_response_keeps_invalid_json_unchanged(tmp_path: Path) -> None:
    result = ex.export_response("NO RESULTS RETURNED", "gp", "json", download_dir=tmp_path, print_preview=False)
    assert result.path.read_text() == "NO RESULTS RETURNED\n"
    assert result.record_count is None

def test_export_response_avoids_overwrite_by_default(tmp_path: Path) -> None:
    first = ex.export_response("a", "gp", "csv", download_dir=tmp_path, timestamp=TS, print_preview=False)
    second = ex.export_response("b", "gp", "csv", download_dir=tmp_path, timestamp=TS, print_preview=False)

    assert first.path.name == f"spacetrack_gp_{TS}.csv"
    assert second.path.name == f"spacetrack_gp_{TS}_1.csv"
    assert first.path.read_text() == "a\n"

def test_export_response_overwrite_true_replaces(tmp_path: Path) -> None:
    ex.export_response("a", "gp", "csv", download_dir=tmp_path, custom_name="out", print_preview=False)
    result = ex.export_response("b", "gp", "csv", download_dir=tmp_path, custom_name="out", overwrite=True, print_preview=False)

    assert result.path.name == "out.csv"
    assert result.path.read_text() == "b\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out.csv"]

def test_export_response_empty_content(tmp_path: Path) -> None:
    result = ex.export_response("", "gp", "csv", download_dir=tmp_path, print_preview=False)

    assert result.size_bytes == 0
    assert result.record_count == 0
    assert result.preview == "<empty response>"

def test_export_binary_response_is_byte_exact(tmp_path: Path) -> None:
    payload = bytes(range(256))
    result = ex.export_binary_response(payload, "publicfiles_download", download_dir=tmp_path, print_preview=False)

    assert result.path.suffix == ".bin"
    assert result.path.read_bytes() == payload
    assert result.record_count is None

def test_export_json_object_and_lines(tmp_path: Path) -> None:
    obj = ex.export_json_object([{"a": 1}], "gp", download_dir=tmp_path, custom_name="obj", print_preview=False)
    lines = ex.export_lines(["1 x", "2 y"], "gp", "tle", download_dir=tmp_path, custom_name="lines", print_preview=False)

    assert json.loads(obj.path.read_text()) == [{"a": 1}]
    assert lines.path.name == "lines.tle"
    assert lines.path.read_text() == "1 x\n2 y\n"
    assert lines.record_count == 1

def test_export_public_file_bytes(tmp_path: Path) -> None:
    first = ex.export_public_file_bytes(b"PK\x03\x04", "Report 2026.ZIP", download_dir=tmp_path, print_preview=False)
    second = ex.export_public_file_bytes(b"PK", "Report 2026.ZIP", download_dir=tmp_path, print_preview=False)

    assert first.path.name == "report_2026.zip"
    assert second.path.name == "report_2026_1.zip"
    assert first.path.read_bytes() == b"PK\x03\x04"
    assert first.preview == "<binary public file: 4 bytes>"

def test_default_download_dir_is_relative_to_cwd(tmp_path: Path) -> None:
    result = ex.export_response("x", "gp", "csv", custom_name="cwd_check", print_preview=False)
    assert result.path.resolve() == (tmp_path / "downloads" / "cwd_check.csv").resolve()

def test_self_test_writes_into_cwd_downloads(tmp_path: Path) -> None:
    ex._self_test()
    assert (tmp_path / "downloads" / "exporter_self_test.json").is_file()
