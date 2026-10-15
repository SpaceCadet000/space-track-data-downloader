# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_query_builder.py
# PATH:         space-track-data-downloader/tests/test_query_builder.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for query_builder.py: path-value encoding, segment order,
#               validation errors, publicfiles URLs, and query summaries.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import pytest
import query_builder as qb
from dataset_configs import get_dataset
from query_builder import (
    BASE_URL,
    InvalidDatasetError,
    InvalidFilterError,
    InvalidFormatError,
    QueryBuilderError,
    SpaceTrackQuery,
)

# =============================================================================
# Encoding
# =============================================================================

@pytest.mark.parametrize(
    "value, encoded",
    [
        ("DEBRIS", "DEBRIS"),
        ("ROCKET BODY", "ROCKET%20BODY"),
        (">now-10", "%3Enow-10"),
        ("<2000", "%3C2000"),
        ("<>null-val", "%3C%3Enull-val"),
        ("25544,43013", "25544,43013"),
        ("25544--26000", "25544--26000"),
        ("STARLINK~~", "STARLINK~~"),
        ("^STAR", "%5ESTAR"),
        ("0.99--1.01", "0.99--1.01"),
        ("50%", "50%25"),
        ("  padded  ", "padded"),
        (25544, "25544"),
    ],
)
def test_encode_path_value(value, encoded) -> None:
    assert qb.encode_path_value(value) == encoded

def test_encode_path_value_escapes_slash_to_prevent_path_injection() -> None:
    assert qb.encode_path_value("A/B") == "A%2FB"

@pytest.mark.parametrize("value", [None, "", "   "])
def test_encode_path_value_rejects_empty(value) -> None:
    with pytest.raises(InvalidFilterError):
        qb.encode_path_value(value)

def test_encode_orderby_value_escapes_space() -> None:
    assert qb.encode_orderby_value("EPOCH desc") == "EPOCH%20desc"

def test_encode_predicates_joins_with_commas() -> None:
    assert qb.encode_predicates(["NORAD_CAT_ID", "EPOCH"]) == "NORAD_CAT_ID,EPOCH"

def test_encode_predicates_rejects_empty_list() -> None:
    with pytest.raises(QueryBuilderError):
        qb.encode_predicates([])

def test_normalize_filters() -> None:
    assert qb.normalize_filters(None) == {}
    assert qb.normalize_filters({" EPOCH ": " >now-1 ", "ID": 5}) == {
        "EPOCH": ">now-1",
        "ID": "5",
    }

@pytest.mark.parametrize(
    "filters",
    [{"": "x"}, {"A": ""}, {"A": None}, ["not", "a", "dict"]],
)
def test_normalize_filters_rejects_bad_input(filters) -> None:
    with pytest.raises(InvalidFilterError):
        qb.normalize_filters(filters)

# =============================================================================
# Path segment helpers
# =============================================================================

def test_build_filter_path() -> None:
    assert qb.build_filter_path({}) == ""
    assert (
        qb.build_filter_path({"OBJECT_TYPE": "DEBRIS", "EPOCH": ">now-10"})
        == "/OBJECT_TYPE/DEBRIS/EPOCH/%3Enow-10"
    )

@pytest.mark.parametrize(
    "limit, offset, expected",
    [(None, None, ""), (10, None, "/limit/10"), (10, 5, "/limit/10,5"), (10, 0, "/limit/10,0")],
)
def test_build_limit_path(limit, offset, expected) -> None:
    assert qb.build_limit_path(limit, offset) == expected

@pytest.mark.parametrize(
    "limit, offset",
    [(None, 5), (0, None), (-1, None), (10, -1), ("10", None), (10, "5")],
)
def test_build_limit_path_rejects_invalid(limit, offset) -> None:
    with pytest.raises(QueryBuilderError):
        qb.build_limit_path(limit, offset)

def test_build_format_path() -> None:
    assert qb.build_format_path(None) == ""
    assert qb.build_format_path("raw") == ""
    assert qb.build_format_path(" JSON ") == "/format/json"

def test_toggle_segments() -> None:
    assert qb.build_distinct_path(False) == ""
    assert qb.build_distinct_path(True) == "/distinct/true"
    assert qb.build_empty_result_path(False) == ""
    assert qb.build_empty_result_path(True) == "/emptyresult/show"
    assert qb.build_favorites_path(None) == ""
    assert qb.build_favorites_path("  ") == ""
    assert qb.build_favorites_path("Special_Interest") == "/favorites/Special_Interest"
    assert qb.build_orderby_path("") == ""
    assert qb.build_predicates_path(None) == ""

@pytest.mark.parametrize(
    "raw, expected",
    [(None, ""), ("  ", ""), ("COMMENTCODE/1/", "/COMMENTCODE/1"), ("/X/Y", "/X/Y")],
)
def test_normalize_raw_extra_path(raw, expected) -> None:
    assert qb.normalize_raw_extra_path(raw) == expected

@pytest.mark.parametrize("fmt", ["csv", "tle", "3le", "kvn"])
def test_metadata_segment_dropped_for_unsupported_formats(fmt) -> None:
    assert qb.build_metadata_path("gp", True, fmt) == ""

def test_metadata_segment_for_supported_format() -> None:
    assert qb.build_metadata_path("gp", True, "json") == "/metadata/true"
    assert qb.build_metadata_path("gp", False, "json") == ""

# =============================================================================
# basicspacedata URLs
# =============================================================================

def test_docstring_example_url() -> None:
    url = qb.build_basicspacedata_url(
        get_dataset("gp"),
        filters={"DECAY_DATE": "null-val", "EPOCH": ">now-10"},
        output_format="json",
    )

    assert url == (
        "https://www.space-track.org/basicspacedata/query/class/gp"
        "/DECAY_DATE/null-val/EPOCH/%3Enow-10/orderby/NORAD_CAT_ID/format/json"
    )

def test_all_segments_in_fixed_order() -> None:
    url = qb.build_basicspacedata_url(
        get_dataset("gp"),
        filters={"OBJECT_TYPE": "ROCKET BODY", "NORAD_CAT_ID": "25544,43013"},
        output_format="json",
        predicates=["NORAD_CAT_ID", "OBJECT_NAME", "EPOCH"],
        orderby="EPOCH desc",
        limit=10,
        offset=5,
        metadata=True,
        show_empty=True,
        favorites="Geosynchronous",
        distinct=True,
        raw_extra_path="COMMENTCODE/1",
    )

    assert url == (
        "https://www.space-track.org/basicspacedata/query/class/gp"
        "/OBJECT_TYPE/ROCKET%20BODY/NORAD_CAT_ID/25544,43013"
        "/favorites/Geosynchronous"
        "/predicates/NORAD_CAT_ID,OBJECT_NAME,EPOCH"
        "/orderby/EPOCH%20desc"
        "/limit/10,5"
        "/distinct/true"
        "/metadata/true"
        "/emptyresult/show"
        "/COMMENTCODE/1"
        "/format/json"
    )

def test_default_orderby_used_when_none() -> None:
    url = qb.build_basicspacedata_url(get_dataset("decay"))
    assert "/orderby/DECAY_EPOCH%20desc/" in url

def test_empty_orderby_skips_default() -> None:
    url = qb.build_basicspacedata_url(get_dataset("decay"), orderby="")
    assert "/orderby/" not in url

def test_default_format_used_when_none() -> None:
    url = qb.build_basicspacedata_url(get_dataset("satcat"))
    assert url.endswith("/format/json")

def test_format_is_normalized() -> None:
    url = qb.build_basicspacedata_url(get_dataset("gp"), output_format=" TLE ")
    assert url.endswith("/format/tle")

def test_unsupported_format_raises() -> None:
    with pytest.raises(InvalidFormatError):
        qb.build_basicspacedata_url(get_dataset("satcat"), output_format="tle")

def test_basicspacedata_builder_rejects_publicfiles_dataset() -> None:
    with pytest.raises(QueryBuilderError, match="basicspacedata"):
        qb.build_basicspacedata_url(get_dataset("publicfiles_dirs"))

def test_custom_base_url_trailing_slash_is_stripped() -> None:
    url = qb.build_basicspacedata_url(get_dataset("boxscore"), base_url="https://example.test/")
    assert url.startswith("https://example.test/basicspacedata/query/class/boxscore")

# =============================================================================
# publicfiles URLs
# =============================================================================

@pytest.mark.parametrize(
    "dataset_key, path",
    [
        ("publicfiles_dirs", "/publicfiles/query/class/dirs"),
        ("publicfiles_files", "/publicfiles/query/class/files"),
        ("publicfiles_loadpublicdata", "/publicfiles/query/class/loadpublicdata"),
    ],
)
def test_publicfiles_listing_urls(dataset_key, path) -> None:
    assert qb.build_query_url(dataset_key) == BASE_URL + path

def test_publicfiles_download_url_encodes_name_as_query_string() -> None:
    url = qb.build_query_url(
        "publicfiles_download",
        publicfiles_download_name="my file&x=1.zip",
    )

    assert url == (
        BASE_URL + "/publicfiles/query/class/download?name=my+file%26x%3D1.zip"
    )

def test_publicfiles_download_name_from_filters() -> None:
    url = qb.build_query_url("publicfiles_download", filters={"name": "a.zip"})
    assert url.endswith("/download?name=a.zip")

def test_publicfiles_download_without_name_raises() -> None:
    with pytest.raises(QueryBuilderError, match="requires a file name"):
        qb.build_query_url("publicfiles_download")

def test_publicfiles_builder_rejects_basicspacedata_dataset() -> None:
    with pytest.raises(QueryBuilderError, match="publicfiles"):
        qb.build_publicfiles_url(get_dataset("gp"))

# =============================================================================
# build_query_url / SpaceTrackQuery
# =============================================================================

def test_build_query_url_unknown_dataset() -> None:
    with pytest.raises(InvalidDatasetError):
        qb.build_query_url("nope")

def test_recommended_filters_off_by_default() -> None:
    url = qb.build_query_url("gp")
    assert "DECAY_DATE" not in url

def test_recommended_filters_merge_and_user_wins() -> None:
    merged = qb.apply_recommended_filters(
        "gp",
        {"EPOCH": ">now-1", "OBJECT_TYPE": "DEBRIS"},
        use_recommended=True,
    )

    assert merged == {
        "DECAY_DATE": "null-val",
        "EPOCH": ">now-1",
        "OBJECT_TYPE": "DEBRIS",
    }

def test_build_query_url_from_object_matches_function() -> None:
    query = SpaceTrackQuery(
        dataset_key="gp",
        filters={"OBJECT_TYPE": "DEBRIS"},
        output_format="csv",
        limit=5,
    )

    assert qb.build_query_url_from_object(query) == qb.build_query_url(
        "gp",
        filters={"OBJECT_TYPE": "DEBRIS"},
        output_format="csv",
        limit=5,
    )

def test_query_object_publicfiles_download_requires_name() -> None:
    with pytest.raises(QueryBuilderError):
        qb.build_query_url_from_object(SpaceTrackQuery(dataset_key="publicfiles_download"))

# =============================================================================
# Model definitions
# =============================================================================

def test_build_modeldef_url() -> None:
    assert qb.build_modeldef_url("gp") == BASE_URL + "/basicspacedata/modeldef/class/gp"

def test_build_modeldef_url_rejects_publicfiles() -> None:
    with pytest.raises(QueryBuilderError):
        qb.build_modeldef_url("publicfiles_dirs")

def test_build_modeldef_url_for_class() -> None:
    assert qb.build_modeldef_url_for_class("satcat") == (
        BASE_URL + "/basicspacedata/modeldef/class/satcat"
    )

    with pytest.raises(QueryBuilderError):
        qb.build_modeldef_url_for_class("  ")

# =============================================================================
# Summaries
# =============================================================================

def test_summarize_query_url_matches_build_query_url() -> None:
    kwargs = dict(
        dataset_key="gp",
        filters={"OBJECT_TYPE": "DEBRIS"},
        output_format="tle",
        limit=3,
        metadata=True,
    )

    summary = qb.summarize_query(**kwargs)

    assert summary["url"] == qb.build_query_url(**kwargs)
    assert summary["relative_path"] == summary["url"][len(BASE_URL):]
    assert summary["orderby"] == "NORAD_CAT_ID"
    assert summary["metadata_requested"] is True
    assert summary["metadata_supported"] is False
    assert summary["output_format"] == "tle"

def test_summarize_query_publicfiles_download_is_raw() -> None:
    summary = qb.summarize_query(
        "publicfiles_download",
        publicfiles_download_name="x.zip",
    )

    assert summary["output_format"] == "raw"
    assert summary["controller"] == "publicfiles"

def test_build_relative_query_path_with_foreign_url() -> None:
    assert qb.build_relative_query_path("https://other.test/x") == "https://other.test/x"

def test_print_query_summary(capsys) -> None:
    summary = qb.summarize_query(
        "gp",
        filters={"OBJECT_TYPE": "DEBRIS"},
        predicates=["NORAD_CAT_ID"],
        limit=2,
        offset=1,
        show_empty=True,
        distinct=True,
        favorites="Geosynchronous",
    )

    qb.print_query_summary(summary)
    out = capsys.readouterr().out

    assert "Limit        : 2, offset 1" in out
    assert "  - OBJECT_TYPE: DEBRIS" in out
    assert "Favorites    : Geosynchronous" in out
    assert summary["url"] in out

# =============================================================================
# Convenience builders
# =============================================================================

def test_build_latest_gp_url() -> None:
    url = qb.build_latest_gp_url(object_type="DEBRIS", epoch_days=7, limit=5)

    assert url == (
        BASE_URL
        + "/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS/DECAY_DATE/null-val"
        "/EPOCH/%3Enow-7/orderby/NORAD_CAT_ID/limit/5/format/json"
    )

def test_build_latest_gp_url_without_optional_filters() -> None:
    url = qb.build_latest_gp_url(on_orbit_only=False, epoch_days=None)
    assert url == BASE_URL + "/basicspacedata/query/class/gp/orderby/NORAD_CAT_ID/format/json"

@pytest.mark.parametrize(
    "builder, kwargs",
    [
        (qb.build_latest_gp_url, {"epoch_days": 0}),
        (qb.build_decay_url, {"recent_msg_days": -1}),
        (qb.build_cdm_public_url, {"created_days": 0}),
    ],
)
def test_convenience_builders_reject_non_positive_days(builder, kwargs) -> None:
    with pytest.raises(QueryBuilderError):
        builder(**kwargs)

def test_other_convenience_builders() -> None:
    assert "/satcat/CURRENT/Y/" in qb.build_satcat_url()
    assert "/decay/MSG_EPOCH/%3Enow-1/" in qb.build_decay_url(recent_msg_days=1)
    assert "/cdm_public/CREATED/%3Enow-1/orderby/CREATED%20desc/" in qb.build_cdm_public_url()

def test_self_test_runs_offline(capsys) -> None:
    qb._self_test()
    assert "Query builder self-test examples" in capsys.readouterr().out
