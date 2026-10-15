# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_dataset_configs.py
# PATH:         space-track-data-downloader/tests/test_dataset_configs.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for dataset_configs.py: dataset definition invariants,
#               preset tables, lookup helpers, and format/metadata rules.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import pytest
import dataset_configs as dc
from dataset_configs import (
    BASIC_SPACE_DATA_CONTROLLER,
    DATASET_GROUPS,
    DATASETS,
    PUBLIC_FILES_CONTROLLER,
)

ALL_DATASET_KEYS = list(DATASETS)

# =============================================================================
# Dataset definition invariants
# =============================================================================

@pytest.mark.parametrize("key", ALL_DATASET_KEYS)
def test_dataset_key_matches_dict_key(key: str) -> None:
    assert DATASETS[key].key == key

@pytest.mark.parametrize("key", ALL_DATASET_KEYS)
def test_default_format_is_supported(key: str) -> None:
    dataset = DATASETS[key]
    assert dataset.default_format in dataset.supported_formats

@pytest.mark.parametrize("key", ALL_DATASET_KEYS)
def test_publicfiles_flag_matches_controller(key: str) -> None:
    dataset = DATASETS[key]
    assert dataset.controller in {BASIC_SPACE_DATA_CONTROLLER, PUBLIC_FILES_CONTROLLER}
    assert dataset.is_publicfiles_endpoint == (dataset.controller == PUBLIC_FILES_CONTROLLER)

@pytest.mark.parametrize("key", ALL_DATASET_KEYS)
def test_tle_flag_matches_supported_formats(key: str) -> None:
    dataset = DATASETS[key]
    supports_tle = {"tle", "3le"} & set(dataset.supported_formats)
    assert dataset.allow_tle_formats == bool(supports_tle)

@pytest.mark.parametrize("key", ALL_DATASET_KEYS)
def test_publicfiles_datasets_have_no_orderby_or_metadata(key: str) -> None:
    dataset = DATASETS[key]

    if dataset.is_publicfiles_endpoint:
        assert dataset.default_orderby is None
        assert dataset.supports_metadata is False

def test_dataset_configs_are_frozen() -> None:
    with pytest.raises(AttributeError):
        DATASETS["gp"].label = "changed"  # type: ignore[misc]

def test_every_dataset_belongs_to_exactly_one_group() -> None:
    membership: dict[str, int] = {key: 0 for key in DATASETS}

    for group in DATASET_GROUPS.values():
        for dataset_key in group["datasets"]:
            assert dataset_key in DATASETS, f"group references unknown {dataset_key!r}"
            membership[dataset_key] += 1

    assert all(count == 1 for count in membership.values()), membership

def test_list_helpers_preserve_insertion_order() -> None:
    assert dc.list_dataset_keys() == list(DATASETS)
    assert dc.list_dataset_group_keys() == list(DATASET_GROUPS)

# =============================================================================
# Lookup helpers
# =============================================================================

def test_get_dataset_returns_config() -> None:
    assert dc.get_dataset("gp") is DATASETS["gp"]

@pytest.mark.parametrize(
    "func, bad_key, message",
    [
        (dc.get_dataset, "nope", "Unknown dataset key"),
        (dc.get_dataset_group, "nope", "Unknown dataset group key"),
        (dc.get_object_type_filter, "nope", "Unknown object-type option"),
        (dc.get_orbit_regime_filter, "nope", "Unknown orbit-regime option"),
        (dc.get_rcs_size_filter, "nope", "Unknown RCS-size option"),
        (dc.get_epoch_recency_filter, "nope", "Unknown epoch-recency option"),
        (dc.get_creation_date_recency_filter, "nope", "Unknown creation-date-recency option"),
        (dc.get_country_code, "nope", "Unknown country option"),
        (dc.get_favorite_value, "nope", "Unknown favorites option"),
    ],
)
def test_unknown_keys_raise_key_error_with_message(func, bad_key, message) -> None:
    with pytest.raises(KeyError, match=message):
        func(bad_key)

def test_get_dataset_is_case_sensitive() -> None:
    with pytest.raises(KeyError):
        dc.get_dataset("GP")

@pytest.mark.parametrize(
    "getter, key",
    [
        (dc.get_object_type_filter, "active_payloads"),
        (dc.get_orbit_regime_filter, "geo_mean_motion"),
        (dc.get_rcs_size_filter, "small"),
        (dc.get_epoch_recency_filter, "10"),
        (dc.get_creation_date_recency_filter, "1_hour"),
    ],
)
def test_preset_getters_return_copies(getter, key) -> None:
    first = getter(key)
    assert first, "expected a non-empty preset"
    first["MUTATED"] = "yes"
    assert "MUTATED" not in getter(key)

def test_get_recommended_filters_returns_copy() -> None:
    filters = dc.get_recommended_filters("gp")
    assert filters == {"DECAY_DATE": "null-val", "EPOCH": ">now-10"}
    filters["EXTRA"] = "1"
    assert "EXTRA" not in DATASETS["gp"].recommended_filters

def test_preset_values() -> None:
    assert dc.get_object_type_filter("active_payloads") == {
        "OBJECT_TYPE": "PAYLOAD",
        "DECAY_DATE": "null-val",
    }
    assert dc.get_object_type_filter("all_objects") == {}
    assert dc.get_epoch_recency_filter("10") == {"EPOCH": ">now-10"}

def test_epoch_recency_keys_are_strings() -> None:
    with pytest.raises(KeyError):
        dc.get_epoch_recency_filter(10)  # type: ignore[arg-type]

def test_country_code_sentinels() -> None:
    assert dc.get_country_code("all") is None
    assert dc.get_country_code("custom") == "custom"
    assert dc.get_country_code("US") == "US"

def test_favorite_value() -> None:
    assert dc.get_favorite_value("geosynchronous") == "Geosynchronous"

def test_predicate_description_fallback() -> None:
    assert dc.get_predicate_description("NORAD_CAT_ID") == "NORAD catalog identifier"
    assert dc.get_predicate_description("NOT_A_PREDICATE") == "No description available"

def test_simple_dataset_accessors() -> None:
    assert dc.get_supported_formats("satcat") == ("json", "csv", "xml", "html")
    assert dc.get_default_format("publicfiles_download") == "raw"
    assert dc.get_default_orderby("gp_history") == "EPOCH desc"
    assert dc.get_default_orderby("publicfiles_dirs") is None
    assert "NORAD_CAT_ID" in dc.get_common_filters("gp")
    assert dc.is_supported_format("gp", "tle") is True
    assert dc.is_supported_format("satcat", "tle") is False

# =============================================================================
# merge_filters
# =============================================================================

def test_merge_filters_later_sets_win_and_inputs_untouched() -> None:
    first = {"A": "1", "B": "2"}
    second = {"B": "override", "C": "3"}

    merged = dc.merge_filters(first, second)

    assert merged == {"A": "1", "B": "override", "C": "3"}
    assert first == {"A": "1", "B": "2"}
    assert second == {"B": "override", "C": "3"}

def test_merge_filters_with_no_arguments() -> None:
    assert dc.merge_filters() == {}

# =============================================================================
# Format and metadata rules
# =============================================================================

def test_validate_dataset_format_accepts_supported() -> None:
    dc.validate_dataset_format("gp", "3le")

def test_validate_dataset_format_rejects_unsupported() -> None:
    with pytest.raises(ValueError, match="not supported"):
        dc.validate_dataset_format("satcat", "tle")

def test_validate_dataset_format_unknown_dataset_is_key_error() -> None:
    with pytest.raises(KeyError):
        dc.validate_dataset_format("nope", "json")

@pytest.mark.parametrize(
    "dataset_key, fmt, expected",
    [
        ("gp", "tle", True),
        ("gp", "3le", True),
        ("gp", "json", False),
        ("satcat", "tle", False),
    ],
)
def test_should_warn_legacy_tle(dataset_key, fmt, expected) -> None:
    assert dc.should_warn_legacy_tle(dataset_key, fmt) is expected

@pytest.mark.parametrize(
    "dataset_key, fmt, expected",
    [
        ("gp", "json", True),
        ("gp", "xml", True),
        ("gp", None, True),
        ("gp", "csv", False),
        ("gp", "tle", False),
        ("gp", "3le", False),
        ("gp", "kvn", False),
        ("publicfiles_dirs", "json", False),
    ],
)
def test_dataset_supports_metadata(dataset_key, fmt, expected) -> None:
    assert dc.dataset_supports_metadata(dataset_key, fmt) is expected

def test_uses_publicfiles_controller() -> None:
    assert dc.dataset_uses_publicfiles_controller("publicfiles_download") is True
    assert dc.dataset_uses_publicfiles_controller("gp") is False

@pytest.mark.parametrize(
    "fmt, extension",
    [
        ("json", ".json"),
        ("CSV", ".csv"),
        ("tle", ".tle"),
        ("3le", ".tle"),
        ("raw", ".bin"),
        ("pdf", ".pdf"),
    ],
)
def test_get_file_extension(fmt, extension) -> None:
    assert dc.get_file_extension(fmt) == extension

def test_safe_dataset_filename_part() -> None:
    assert dc.get_safe_dataset_filename_part("GP History/x") == "gp_history_x"

# =============================================================================
# Print helpers
# =============================================================================

def test_print_available_datasets_lists_every_dataset(capsys) -> None:
    dc.print_available_datasets()
    out = capsys.readouterr().out

    for key in DATASETS:
        assert f"- {key}:" in out

def test_print_dataset_details(capsys) -> None:
    dc.print_dataset_details("gp")
    out = capsys.readouterr().out

    assert "Key: gp" in out
    assert "Default orderby: NORAD_CAT_ID" in out
    assert "NORAD_CAT_ID: NORAD catalog identifier" in out
    assert "DECAY_DATE: null-val" in out
