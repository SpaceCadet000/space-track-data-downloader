# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_downloader_core.py
# PATH:         space-track-data-downloader/tests/test_downloader_core.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for downloader_core.py: filter specs, filter/query-option
#               assembly (with parity against the terminal wizard), query
#               preparation, export stages, previews, and download history.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import downloader_core as core
import spacetrack_downloader as sd
from dataset_configs import COUNTRY_PRESETS, DATASETS, OBJECT_TYPE_FILTERS, get_dataset
from exporters import ExportResult
from spacetrack_client import SpaceTrackResponse

def menu_number(keys: list[str], key: str) -> str:
    return str(list(keys).index(key) + 1)

def response(text: str = '[{"NORAD_CAT_ID": "25544"}]', content: bytes | None = None) -> SpaceTrackResponse:
    return SpaceTrackResponse(
        url="https://www.space-track.org/fake",
        status_code=200,
        text=text,
        content=content if content is not None else text.encode("utf-8"),
        headers={"Content-Type": "application/json", "Set-Cookie": "secret"},
        elapsed_seconds=0.5,
    )

def export_options(download_dir: Path, **overrides: Any) -> dict[str, Any]:
    options = {"download_dir": download_dir, "custom_name": None, "overwrite": False, "pretty_json": True}
    options.update(overrides)
    return options

# =============================================================================
# Filter specs
# =============================================================================

def test_every_dataset_has_a_filter_spec_with_unique_ids() -> None:
    for key in DATASETS:
        ids = [spec.id for spec in core.dataset_filter_fields(key)]
        assert len(ids) == len(set(ids)), key

def test_gp_and_gp_history_field_order() -> None:
    gp = [spec.id for spec in core.dataset_filter_fields("gp")]
    history = [spec.id for spec in core.dataset_filter_fields("gp_history")]

    assert gp[0] == "object_type"
    assert gp.index("country") < gp.index("norad") < gp.index("name")
    assert gp[-2:] == ["custom", "favorites"]
    assert history[0] == "norad" and "object_type" not in history

def test_dataset_flow_routing() -> None:
    assert core.dataset_flow("gp_history") == "gp_like"
    assert core.dataset_flow("launch_site") == "satcat"
    assert core.dataset_flow("tip") == "decay"
    assert core.dataset_flow("publicfiles_download") == "publicfiles"

def test_dataset_warning_only_for_gp_history() -> None:
    assert core.dataset_warning("gp_history") == core.GP_HISTORY_WARNING
    assert core.dataset_warning("gp") is None

def test_field_choices() -> None:
    gp = {spec.id: spec for spec in core.dataset_filter_fields("gp")}

    assert [key for key, _ in gp["object_type"].choices()] == list(OBJECT_TYPE_FILTERS)
    assert [key for key, _ in gp["country"].choices()] == list(COUNTRY_PRESETS)
    assert gp["favorites"].choices() == core.favorite_options()

# =============================================================================
# Resolvers
# =============================================================================

def test_resolve_preset() -> None:
    assert core.resolve_preset("object_type", "debris_on_orbit") == dict(OBJECT_TYPE_FILTERS["debris_on_orbit"]["filters"])

    with pytest.raises(core.CoreError):
        core.resolve_preset("object_type", "nope")

    with pytest.raises(core.CoreError):
        core.resolve_preset("nope", "all")

def test_resolve_country() -> None:
    assert core.resolve_country("COUNTRY", "all") == {}
    assert core.resolve_country("COUNTRY", "PRC") == {"COUNTRY": "PRC"}
    assert core.resolve_country("COUNTRY_CODE", "custom", " isra ") == {"COUNTRY_CODE": "ISRA"}

    with pytest.raises(core.CoreError):
        core.resolve_country("COUNTRY", "custom", "")

    with pytest.raises(core.CoreError):
        core.resolve_country("COUNTRY", "atlantis")

def test_resolve_favorites() -> None:
    assert core.resolve_favorites("geosynchronous") == "Geosynchronous"

    with pytest.raises(core.CoreError):
        core.resolve_favorites("nope")

def test_normalize_custom_filters() -> None:
    assert core.normalize_custom_filters(None) == {}
    assert core.normalize_custom_filters({"epoch": ">now-1"}) == {"EPOCH": ">now-1"}
    assert core.normalize_custom_filters([["a", "1"], {"predicate": "b", "value": "2"}, ["", ""]]) == {"A": "1", "B": "2"}

    for bad in ("x", [["a"]], [["a", ""]]):
        with pytest.raises(core.CoreError):
            core.normalize_custom_filters(bad)

# =============================================================================
# build_filter_config
# =============================================================================

def test_build_filter_config_defaults_and_unknown_fields() -> None:
    assert core.build_filter_config("gp", {}) == {"filters": {"DECAY_DATE": "null-val"}, "favorites": None}

    with pytest.raises(core.CoreError):
        core.build_filter_config("gp", {"bogus": "x"})

def test_build_filter_config_gp_choices() -> None:
    result = core.build_filter_config(
        "gp",
        {
            "object_type": "debris_on_orbit",
            "epoch_recency": "7",
            "country": "US",
            "norad": "25544,43013",
            "name": "ISS~~",
            "site": "afetr",
            "custom": [["period", "<128"]],
            "favorites": "geosynchronous",
        },
    )

    assert result == {
        "filters": {
            "OBJECT_TYPE": "DEBRIS",
            "DECAY_DATE": "null-val",
            "EPOCH": ">now-7",
            "COUNTRY_CODE": "US",
            "NORAD_CAT_ID": "25544,43013",
            "OBJECT_NAME": "ISS~~",
            "SITE": "AFETR",
            "PERIOD": "<128",
        },
        "favorites": "Geosynchronous",
    }

def test_build_filter_config_flags_and_empty_text() -> None:
    result = core.build_filter_config("satcat", {"current": True, "on_orbit": False, "norad": "  "})
    assert result == {"filters": {"CURRENT": "Y"}, "favorites": None}

def test_null_value_hints_flag_null_but_not_null_val() -> None:
    values = {
        "norad": "null",
        "name": " NULL ",
        "launch_date": "null-val",
        "object_type": "all_on_orbit",
        "custom": [["DECAY_DATE", "null"], ["PERIOD", "1430--1450"], ["RCS_SIZE", "null-val"]],
    }

    hints = core.null_value_hints(values)

    assert [(h["field"], h.get("index")) for h in hints] == [("norad", None), ("name", None), ("custom", 0)]
    assert all("null-val" in h["message"] for h in hints)
    assert core.null_value_hints(None) == []

def test_null_value_hints_leave_values_unchanged() -> None:
    values = {"custom": [["DECAY_DATE", "null"]]}
    core.null_value_hints(values)
    assert core.build_filter_config("gp", values)["filters"]["DECAY_DATE"] == "null"

def test_build_filter_config_publicfiles() -> None:
    assert core.build_filter_config("publicfiles_dirs", {}) == {
        "filters": {},
        "favorites": None,
        "publicfiles_download_name": None,
    }
    assert core.build_filter_config("publicfiles_download", {"publicfile_name": "Report 2026.zip"}) == {
        "filters": {"name": "Report 2026.zip"},
        "favorites": None,
        "publicfiles_download_name": "Report 2026.zip",
    }

def test_build_filter_config_with_explicit_fields() -> None:
    result = core.build_filter_config("gp", {"custom": {"x": "1"}}, fields=[core.CUSTOM_FIELD])
    assert result == {"filters": {"X": "1"}, "favorites": None}

@pytest.mark.parametrize("dataset_key", [key for key in DATASETS if key != "publicfiles_download"])
def test_default_values_match_cli_all_enter(scripted_input, dataset_key) -> None:
    scripted_input.enter_for_all()

    cli = sd.configure_dataset_filters(get_dataset(dataset_key))

    assert core.build_filter_config(dataset_key, core.default_filter_values(dataset_key)) == cli

def test_cli_parity_with_choices(scripted_input) -> None:
    scripted_input.set(
        "",                                                     # NORAD
        "y", ">now-3",                                          # MSG_EPOCH
        "n",                                                    # DECAY_EPOCH
        "y", "ISS~~",                                           # OBJECT_NAME
        menu_number(list(COUNTRY_PRESETS), "custom"), "isra",   # country
        "", "y", "4",                                           # RCS, PRECEDENCE
        "y", "epoch", ">now-1", "",                             # custom
    )

    cli = sd.configure_dataset_filters(get_dataset("decay"))
    gui = core.build_filter_config(
        "decay",
        {
            "msg_epoch": ">now-3",
            "name": "ISS~~",
            "country": {"preset": "custom", "custom": "isra"},
            "precedence": "4",
            "custom": {"EPOCH": ">now-1"},
        },
    )

    assert cli == gui

# =============================================================================
# Query options
# =============================================================================

def test_query_option_availability() -> None:
    assert core.query_option_availability("gp", "json") == dict.fromkeys(
        ["predicates", "orderby", "limit", "offset", "metadata", "show_empty", "distinct"], True
    )

    tle = core.query_option_availability("gp", "tle")
    assert not tle["predicates"] and not tle["metadata"] and tle["limit"]

    publicfiles = core.query_option_availability("publicfiles_dirs", "json")
    assert publicfiles["predicates"] and not any(v for k, v in publicfiles.items() if k != "predicates")

def test_normalize_query_options_drops_unavailable() -> None:
    options = core.normalize_query_options(
        "gp",
        {"output_format": "tle", "predicates": ["A"], "metadata": True, "limit": "10", "offset": 5, "orderby": " EPOCH desc "},
    )

    assert options == {
        "output_format": "tle",
        "predicates": None,
        "orderby": "EPOCH desc",
        "limit": 10,
        "offset": 5,
        "metadata": False,
        "show_empty": True,
        "distinct": False,
    }

def test_normalize_query_options_predicates_from_string() -> None:
    assert core.normalize_query_options("gp", {"predicates": "A, ,B"})["predicates"] == ["A", "B"]

@pytest.mark.parametrize(
    "raw",
    [
        {"output_format": "pdf"},
        {"limit": 0},
        {"limit": "x"},
        {"limit": True},
        {"offset": 3},
        {"limit": 1, "offset": -1},
    ],
)
def test_normalize_query_options_rejects(raw) -> None:
    with pytest.raises(core.CoreError):
        core.normalize_query_options("gp", raw)

def test_default_query_options_match_cli(scripted_input) -> None:
    scripted_input.set(*[""] * 7)
    assert core.default_query_options("gp") == sd.configure_query_options(get_dataset("gp"))

    scripted_input.set("", "")
    assert core.default_query_options("publicfiles_dirs") == sd.configure_query_options(get_dataset("publicfiles_dirs"))

def test_format_warning() -> None:
    assert core.format_warning("gp", "tle") == core.LEGACY_TLE_WARNING
    assert core.format_warning("gp", "json") is None

# =============================================================================
# prepare_query and export stages
# =============================================================================

def test_prepare_query_url_and_summary_agree() -> None:
    prepared = core.prepare_query(
        dataset_key="gp",
        filters={"OBJECT_TYPE": "DEBRIS"},
        favorites=None,
        publicfiles_download_name=None,
        query_options=core.normalize_query_options("gp", {"orderby": "NORAD_CAT_ID", "limit": 5, "show_empty": False}),
    )

    assert prepared.url == (
        "https://www.space-track.org/basicspacedata/query/class/gp"
        "/OBJECT_TYPE/DEBRIS/orderby/NORAD_CAT_ID/limit/5/format/json"
    )
    assert prepared.summary["url"] == prepared.url
    assert prepared.output_format == "json"

def test_fetch_uses_download_timeout() -> None:
    calls = []

    class Client:
        download_timeout_seconds = 300

        def get(self, url, *, timeout_seconds=None):
            calls.append((url, timeout_seconds))
            return "ok"

    assert core.fetch(Client(), "https://www.space-track.org/x") == "ok"
    assert calls == [("https://www.space-track.org/x", 300)]

@pytest.mark.parametrize(
    "custom, link, expected",
    [
        (None, "Report 2026.zip", "Report 2026.zip"),
        ("mine", "Report 2026.zip", "mine.zip"),
        ("mine.tar", "Report.zip", "mine.tar"),
        (None, None, "space_track_public_file"),
    ],
)
def test_public_file_output_name(custom, link, expected) -> None:
    assert core.public_file_output_name(custom, link) == expected

def test_export_download_text_and_metadata(tmp_path: Path) -> None:
    prepared = core.prepare_query(
        dataset_key="gp", filters={}, favorites=None, publicfiles_download_name=None,
        query_options=core.normalize_query_options("gp", {}),
    )
    resp = response()

    result = core.export_download(
        response=resp, dataset_key="gp", output_format="json",
        publicfiles_download_name=None, export_options=export_options(tmp_path),
    )
    meta_path = core.save_download_metadata(prepared=prepared, export_result=result, response=resp, overwrite=False)

    assert json.loads(result.path.read_text()) == [{"NORAD_CAT_ID": "25544"}]
    meta = json.loads(meta_path.read_text())
    assert meta["query_url"] == prepared.url
    assert "Set-Cookie" not in meta["response_headers"]

def test_export_download_raw_and_public_file(tmp_path: Path) -> None:
    raw = core.export_download(
        response=response(content=b"\x00\x01"), dataset_key="gp", output_format="raw",
        publicfiles_download_name=None, export_options=export_options(tmp_path),
    )
    public = core.export_download(
        response=response(content=b"PK"), dataset_key="publicfiles_download", output_format="raw",
        publicfiles_download_name="Report.zip", export_options=export_options(tmp_path, custom_name="mine"),
    )

    assert raw.path.read_bytes() == b"\x00\x01"
    assert public.filename == "mine.zip"

def test_resolve_download_dir(tmp_path: Path) -> None:
    assert core.resolve_download_dir("") == Path("downloads")
    assert core.resolve_download_dir("sub/dir") == Path("downloads/sub/dir")
    assert core.resolve_download_dir("downloads/x") == Path("downloads/x")

    for bad in ("../elsewhere", "/etc", "downloads/../.."):
        with pytest.raises(core.CoreError):
            core.resolve_download_dir(bad)

# =============================================================================
# Previews and history
# =============================================================================

def test_table_preview_json_and_csv() -> None:
    table = core.table_preview('[{"A": 1, "B": null}, {"A": 2, "C": {"x": 1}}]', "json")
    assert table == {"columns": ["A", "B", "C"], "rows": [["1", "", ""], ["2", "", '{"x": 1}']], "total": 2}

    assert core.table_preview("A,B\n1,2\n", "csv") == {"columns": ["A", "B"], "rows": [["1", "2"]], "total": 1}
    assert core.table_preview('{"x": 1}', "json") is None
    assert core.table_preview("not json", "json") is None
    assert core.table_preview("x", "tle") is None

def test_read_output_preview(tmp_path: Path) -> None:
    base = tmp_path / "downloads"
    base.mkdir()
    (base / "a.csv").write_text("A,B\n1,2\n")
    (base / "b.bin").write_bytes(b"\x00" * 10)

    preview = core.read_output_preview(base / "a.csv", "csv", base)
    assert preview["table"]["rows"] == [["1", "2"]]
    assert core.read_output_preview(base / "b.bin", "raw", base)["text"].startswith("<binary content")

    with pytest.raises(core.CoreError):
        core.read_output_preview(base / ".." / "outside.csv", "csv", base)

    with pytest.raises(core.CoreError):
        core.read_output_preview(base / "missing.csv", "csv", base)

def test_list_download_history(tmp_path: Path) -> None:
    base = tmp_path / "downloads"
    (base / "sub").mkdir(parents=True)
    output = base / "old.json"
    output.write_text("[]")

    (base / "old_meta.json").write_text(json.dumps({
        "created_utc": "2026-01-01T00:00:00Z", "dataset_key": "gp", "query_url": "u1", "output_file": str(output),
    }))
    (base / "sub" / "new_meta.json").write_text(json.dumps({
        "created_utc": "2026-02-01T00:00:00Z", "dataset_key": "satcat", "query_url": "u2", "output_file": str(base / "gone.json"),
    }))
    (base / "broken_meta.json").write_text("{nope")
    (base / "other_meta.json").write_text("{}")

    listing = core.list_download_history(base)

    assert [entry["dataset_key"] for entry in listing.entries] == ["satcat", "gp"]
    assert [entry["output_exists"] for entry in listing.entries] == [False, True]
    assert len(listing.errors) == 2

def test_list_download_history_missing_dir(tmp_path: Path) -> None:
    listing = core.list_download_history(tmp_path / "nothing")
    assert listing.entries == [] and listing.errors == []

# =============================================================================
# Catalog descriptions
# =============================================================================

def test_dataset_catalog_and_describe_dataset_are_json() -> None:
    catalog = core.dataset_catalog()
    assert [d["key"] for g in catalog for d in g["datasets"]]

    for key in DATASETS:
        description = core.describe_dataset(key)
        json.dumps(description)
        assert description["key"] == key
        assert {fmt["key"] for fmt in description["formats"]} == set(DATASETS[key].supported_formats)

def test_core_module_has_no_prompts() -> None:
    source = Path(core.__file__).read_text()
    code = source.split("# DESCRIPTION", 1)[1].split("\n# ━", 1)[1]
    assert "input(" not in code and "print(" not in code
