# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         test_spacetrack_downloader.py
# PATH:         space-track-data-downloader/tests/test_spacetrack_downloader.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Tests for spacetrack_downloader.py: prompt helpers, filter
#               wizards, query/export option flows, the download pipeline,
#               and the main menu/entry point. Input is scripted and the
#               Space-Track client is faked.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import pytest
import downloader_core
import spacetrack_downloader as sd
from dataset_configs import (
    COUNTRY_PRESETS,
    DATASET_GROUPS,
    DATASETS,
    EPOCH_RECENCY_FILTERS,
    OBJECT_TYPE_FILTERS,
    get_dataset,
)
from spacetrack_client import (
    SpaceTrackAuthenticationError,
    SpaceTrackClientError,
    SpaceTrackRequestError,
    SpaceTrackResponse,
)

OPTIONS = [("a", "Option A"), ("b", "Option B")]

def menu_number(keys: list[str], key: str) -> str:
    """
    Return the 1-based menu number of key as typed by a user.
    """
    return str(list(keys).index(key) + 1)

# =============================================================================
# Fakes
# =============================================================================

class FakeClient:
    """
    Stand-in for SpaceTrackClient as used by the downloader.
    """

    def __init__(self, response: SpaceTrackResponse | Exception | None = None) -> None:
        self.response = response
        self.download_timeout_seconds = 300
        self.get_calls: list[tuple[str, int | None]] = []
        self.logged_in = True
        self.logout_called = False
        self.close_called = False
        self.status_checks = 0

    def get(self, url: str, *, timeout_seconds: int | None = None) -> SpaceTrackResponse:
        self.get_calls.append((url, timeout_seconds))

        if isinstance(self.response, Exception):
            raise self.response

        assert self.response is not None
        return self.response

    def logout(self) -> None:
        self.logout_called = True
        self.logged_in = False

    def close(self) -> None:
        self.close_called = True

    def print_session_status(self) -> None:
        self.status_checks += 1

def ok_response(text: str = '[{"NORAD_CAT_ID": "25544"}]', content: bytes | None = None) -> SpaceTrackResponse:
    return SpaceTrackResponse(
        url="https://www.space-track.org/fake",
        status_code=200,
        text=text,
        content=content if content is not None else text.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        elapsed_seconds=0.25,
    )

def json_query_options(**overrides: Any) -> dict[str, Any]:
    options = {
        "output_format": "json",
        "predicates": None,
        "orderby": None,
        "limit": None,
        "offset": None,
        "metadata": False,
        "show_empty": False,
        "distinct": False,
    }
    options.update(overrides)
    return options

# =============================================================================
# Prompt helpers
# =============================================================================

def test_prompt_text(scripted_input) -> None:
    scripted_input.set("", "   ", "  value  ", "")

    assert sd.prompt_text("Name", default="dflt") == "dflt"
    assert sd.prompt_text("Name") == "value"
    assert sd.prompt_text("Name", allow_empty=True) == ""
    assert scripted_input.prompts[0] == "Name [dflt]: "

def test_prompt_yes_no(scripted_input) -> None:
    scripted_input.set("", "", "maybe", "YES", "n")

    assert sd.prompt_yes_no("Go?", default=True) is True
    assert sd.prompt_yes_no("Go?", default=False) is False
    assert sd.prompt_yes_no("Go?") is True
    assert sd.prompt_yes_no("Go?") is False
    assert scripted_input.prompts[1] == "Go? [y/N]: "

def test_prompt_int(scripted_input) -> None:
    scripted_input.set("abc", "0", "11", "5", "", "", "x", "3")

    assert sd.prompt_int("N", min_value=1, max_value=10) == 5
    assert sd.prompt_int("N", default=7) == 7
    assert sd.prompt_int("N", allow_empty=True) is None
    assert sd.prompt_int("N") == 3

def test_prompt_choice_numbers_back_and_quit(scripted_input) -> None:
    scripted_input.set("2", "3", "4", "", "x", "0", "9", "1")

    assert sd.prompt_choice("T", OPTIONS, allow_back=True, allow_quit=True) == "b"
    assert sd.prompt_choice("T", OPTIONS, allow_back=True, allow_quit=True) == "__back__"
    assert sd.prompt_choice("T", OPTIONS, allow_back=True, allow_quit=True) == "__quit__"
    assert sd.prompt_choice("T", OPTIONS, default_key="b") == "b"
    assert sd.prompt_choice("T", OPTIONS) == "a"

def test_prompt_choice_quit_without_back(scripted_input) -> None:
    scripted_input.set("3")
    assert sd.prompt_choice("T", OPTIONS, allow_quit=True) == "__quit__"

def test_prompt_choice_validates_arguments() -> None:
    with pytest.raises(ValueError):
        sd.prompt_choice("T", [])

    with pytest.raises(ValueError):
        sd.prompt_choice("T", OPTIONS, default_key="zzz")

def test_prompt_multi_choice(scripted_input) -> None:
    options = [("a", "A"), ("b", "B"), ("c", "C")]
    scripted_input.set("all", "2,1,2", "5", "1,x", "none", "")

    assert sd.prompt_multi_choice("T", options) == ["a", "b", "c"]
    assert sd.prompt_multi_choice("T", options) == ["b", "a"]
    assert sd.prompt_multi_choice("T", options) == []
    assert sd.prompt_multi_choice("T", options) == []

def test_prompt_multi_choice_empty_options_does_not_prompt(scripted_input) -> None:
    assert sd.prompt_multi_choice("T", []) == []

# =============================================================================
# Option builders and filter helpers
# =============================================================================

def test_dataset_group_options() -> None:
    keys = [key for key, _ in sd.dataset_group_options()]
    assert keys == list(DATASET_GROUPS) + ["advanced_custom", "session_status"]

def test_dataset_options_for_group() -> None:
    keys = [key for key, _ in sd.dataset_options_for_group("catalog")]
    assert keys == list(DATASET_GROUPS["catalog"]["datasets"])

def test_format_options_for_dataset() -> None:
    assert sd.format_options_for_dataset("publicfiles_download") == [("raw", "RAW")]
    assert [key for key, _ in sd.format_options_for_dataset("gp")] == list(DATASETS["gp"].supported_formats)

def test_preset_option_builders_match_tables() -> None:
    assert [key for key, _ in sd.object_type_options()] == list(OBJECT_TYPE_FILTERS)
    assert [key for key, _ in sd.country_options()] == list(COUNTRY_PRESETS)

def test_merge_and_remove_empty_filters() -> None:
    base = {"A": "1"}
    merged = sd.merge_filters(base, {"A": "2", "B": "3"})

    assert merged == {"A": "2", "B": "3"}
    assert base == {"A": "1"}
    assert sd.remove_empty_filters({"A": "", "B": "  ", "C": "x"}) == {"C": "x"}

# =============================================================================
# ask_* helpers
# =============================================================================

def test_ask_country_filter(scripted_input) -> None:
    countries = list(COUNTRY_PRESETS)
    scripted_input.set("", menu_number(countries, "PRC"), menu_number(countries, "custom"), "isra")

    assert sd.ask_country_filter("COUNTRY") == {}
    assert sd.ask_country_filter("COUNTRY") == {"COUNTRY": "PRC"}
    assert sd.ask_country_filter("COUNTRY_CODE") == {"COUNTRY_CODE": "ISRA"}

def test_ask_favorites_filter(scripted_input) -> None:
    scripted_input.set("", "y", "")

    assert sd.ask_favorites_filter() is None
    assert sd.ask_favorites_filter() == "Geosynchronous"

def test_ask_limit_and_offset(scripted_input) -> None:
    scripted_input.set("", "y", "0", "25", "y", "-1", "10")

    assert sd.ask_limit() is None
    assert sd.ask_limit() == 25
    assert sd.ask_offset(None) is None
    assert sd.ask_offset(25) == 10

def test_ask_orderby(scripted_input) -> None:
    scripted_input.set("", "n", "", "n", "y", "EPOCH desc", "y", "CREATED desc")

    gp = get_dataset("gp")
    assert sd.ask_orderby(gp) == "NORAD_CAT_ID"
    assert sd.ask_orderby(gp) is None
    assert sd.ask_orderby(gp) == "EPOCH desc"
    assert sd.ask_orderby(get_dataset("publicfiles_dirs")) == "CREATED desc"

def test_ask_predicates(scripted_input) -> None:
    common = list(DATASETS["gp"].common_filters)
    scripted_input.set("", "y", "1,3", "y", "none", "A, ,B")

    assert sd.ask_predicates("gp") is None
    assert sd.ask_predicates("gp") == [common[0], common[2]]
    assert sd.ask_predicates("gp") == ["A", "B"]

def test_ask_custom_filters(scripted_input) -> None:
    scripted_input.set("", "y", "epoch", ">now-30", "y", "epoch", ">now-1", "y", "object_name", "ISS", "")

    assert sd.ask_custom_filters() == {}
    assert sd.ask_custom_filters() == {"EPOCH": ">now-1", "OBJECT_NAME": "ISS"}

# =============================================================================
# Dataset configuration wizards
# =============================================================================

def test_configure_gp_all_defaults(scripted_input) -> None:
    scripted_input.set(*[""] * 14)

    assert sd.configure_dataset_filters(get_dataset("gp")) == {
        "filters": {"DECAY_DATE": "null-val"},
        "favorites": None,
    }

def test_configure_gp_with_choices(scripted_input) -> None:
    scripted_input.set(
        menu_number(list(OBJECT_TYPE_FILTERS), "debris_on_orbit"),
        "n",                                                   # orbit regime
        "",                                                    # RCS
        "y", menu_number(list(EPOCH_RECENCY_FILTERS), "7"),    # EPOCH recency
        "",                                                    # CREATION_DATE
        menu_number(list(COUNTRY_PRESETS), "US"),              # country
        "y", "25544,43013",                                    # NORAD
        "y", "ISS~~",                                          # OBJECT_NAME
        "y", "afetr",                                          # SITE
        "",                                                    # LAUNCH_DATE
        "y", "period", "<128", "",                             # custom filters
        "y", "",                                               # favorites
    )

    result = sd.configure_dataset_filters(get_dataset("gp"))

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

def test_configure_gp_history_all_defaults(scripted_input) -> None:
    scripted_input.enter_for_all()

    assert sd.configure_dataset_filters(get_dataset("gp_history")) == {"filters": {}, "favorites": None}

def test_configure_gp_history_asks_norad_once(scripted_input) -> None:
    scripted_input.enter_for_all()

    sd.configure_dataset_filters(get_dataset("gp_history"))

    norad_prompts = [p for p in scripted_input.prompts if "NORAD catalog ID" in p]
    assert len(norad_prompts) == 1

@pytest.mark.parametrize(
    "dataset_key, answers, expected_filters",
    [
        ("satcat", [""] * 10, {"CURRENT": "Y"}),
        ("satcat_debut", [""] * 6, {"DEBUT": ">now-1"}),
        ("satcat_change", [""] * 6, {"CHANGE_DATE": ">now-7"}),
        ("launch_site", ["y", "afetr", "", ""], {"SITE_CODE": "AFETR"}),
        ("decay", [""] * 9, {"DECAY_EPOCH": ">now-7"}),
        ("tip", [""] * 5 + ["y", ""], {"INSERT_EPOCH": ">now-0.042", "HIGH_INTEREST": "Y"}),
        ("cdm_public", [""] * 9, {"CREATED": ">now-1"}),
        ("boxscore", ["y", menu_number(list(COUNTRY_PRESETS), "JPN"), ""], {"COUNTRY": "JPN"}),
    ],
)
def test_configure_other_datasets(scripted_input, dataset_key, answers, expected_filters) -> None:
    scripted_input.set(*answers)

    result = sd.configure_dataset_filters(get_dataset(dataset_key))

    assert result == {"filters": expected_filters, "favorites": None}

def test_configure_decay_with_date_filters(scripted_input) -> None:
    scripted_input.set(
        "",                       # NORAD
        "y", ">now-3",            # MSG_EPOCH
        "y", ">now-7",            # DECAY_EPOCH
        "", "", "", "y", "4", "", # name, country, RCS, PRECEDENCE, custom
    )

    result = sd.configure_dataset_filters(get_dataset("decay"))

    assert result["filters"] == {"MSG_EPOCH": ">now-3", "DECAY_EPOCH": ">now-7", "PRECEDENCE": "4"}

def test_configure_decay_object_name_asked_once(scripted_input) -> None:
    scripted_input.set(
        "",                       # NORAD
        "",                       # MSG_EPOCH
        "n",                      # DECAY_EPOCH
        "y", "ISS~~",             # OBJECT_NAME
        "", "", "", "",           # country, RCS, PRECEDENCE, custom
    )

    result = sd.configure_dataset_filters(get_dataset("decay"))

    assert result["filters"] == {"OBJECT_NAME": "ISS~~"}
    name_questions = [p for p in scripted_input.prompts if "object" in p.lower() and "[y/N]" in p]
    assert len(name_questions) == 1

@pytest.mark.parametrize(
    "dataset_key, predicate",
    [
        ("cdm_public", "CREATED"),
        ("tip", "INSERT_EPOCH"),
        ("decay", "DECAY_EPOCH"),
        ("satcat_change", "CHANGE_DATE"),
    ],
)
def test_default_yes_date_prompt_adds_filter(scripted_input, dataset_key, predicate) -> None:
    scripted_input.enter_for_all()

    result = sd.configure_dataset_filters(get_dataset(dataset_key))

    assert predicate in result["filters"]

def test_configure_publicfiles(scripted_input) -> None:
    assert sd.configure_dataset_filters(get_dataset("publicfiles_dirs")) == {
        "filters": {},
        "favorites": None,
        "publicfiles_download_name": None,
    }

    scripted_input.set("Report 2026.zip")

    assert sd.configure_dataset_filters(get_dataset("publicfiles_download")) == {
        "filters": {"name": "Report 2026.zip"},
        "favorites": None,
        "publicfiles_download_name": "Report 2026.zip",
    }

def test_configure_generic_dataset(scripted_input) -> None:
    scripted_input.set("y", "x", "1", "")
    assert sd.configure_generic_dataset(get_dataset("gp")) == {"filters": {"X": "1"}, "favorites": None}

@pytest.mark.parametrize(
    "dataset_key, flow_name",
    [
        ("gp", "configure_gp_like_dataset"),
        ("gp_history", "configure_gp_like_dataset"),
        ("satcat", "configure_satcat_dataset"),
        ("satcat_change", "configure_satcat_dataset"),
        ("satcat_debut", "configure_satcat_dataset"),
        ("launch_site", "configure_satcat_dataset"),
        ("decay", "configure_decay_dataset"),
        ("tip", "configure_decay_dataset"),
        ("cdm_public", "configure_cdm_dataset"),
        ("boxscore", "configure_boxscore_dataset"),
        ("publicfiles_dirs", "configure_publicfiles_dataset"),
        ("publicfiles_download", "configure_publicfiles_dataset"),
    ],
)
def test_configure_dataset_filters_routing(monkeypatch, dataset_key, flow_name) -> None:
    monkeypatch.setattr(sd, flow_name, lambda dataset: {"routed_to": flow_name, "key": dataset.key})
    assert sd.configure_dataset_filters(get_dataset(dataset_key)) == {"routed_to": flow_name, "key": dataset_key}

def test_every_dataset_has_a_dedicated_flow(monkeypatch) -> None:
    monkeypatch.setattr(sd, "configure_generic_dataset", lambda dataset: pytest.fail(f"{dataset.key} fell back to generic"))
    monkeypatch.setattr(sd, "configure_gp_like_dataset", lambda d: {})
    monkeypatch.setattr(sd, "configure_satcat_dataset", lambda d: {})
    monkeypatch.setattr(sd, "configure_decay_dataset", lambda d: {})
    monkeypatch.setattr(sd, "configure_cdm_dataset", lambda d: {})
    monkeypatch.setattr(sd, "configure_boxscore_dataset", lambda d: {})
    monkeypatch.setattr(sd, "configure_publicfiles_dataset", lambda d: {})

    for dataset in DATASETS.values():
        sd.configure_dataset_filters(dataset)

# =============================================================================
# Query and export options
# =============================================================================

def test_configure_query_options_gp_defaults(scripted_input) -> None:
    scripted_input.set(*[""] * 7)

    assert sd.configure_query_options(get_dataset("gp")) == {
        "output_format": "json",
        "predicates": None,
        "orderby": "NORAD_CAT_ID",
        "limit": None,
        "offset": None,
        "metadata": False,
        "show_empty": True,
        "distinct": False,
    }

def test_configure_query_options_tle(scripted_input, capsys) -> None:
    scripted_input.set(
        menu_number(list(DATASETS["gp"].supported_formats), "tle"),
        "",            # default orderby
        "y", "10",     # limit
        "y", "5",      # offset
        "",            # show empty
        "y",           # distinct
    )

    options = sd.configure_query_options(get_dataset("gp"))

    assert options == {
        "output_format": "tle",
        "predicates": None,
        "orderby": "NORAD_CAT_ID",
        "limit": 10,
        "offset": 5,
        "metadata": False,
        "show_empty": True,
        "distinct": True,
    }
    assert "TLE/3LE are legacy" in capsys.readouterr().out
    assert not any("metadata" in p for p in scripted_input.prompts)

def test_configure_query_options_publicfiles(scripted_input) -> None:
    scripted_input.set("", "")

    options = sd.configure_query_options(get_dataset("publicfiles_dirs"))

    assert options["output_format"] == "json"
    assert (options["orderby"], options["limit"], options["show_empty"]) == (None, None, False)

def test_configure_query_options_raw_skips_predicates(scripted_input) -> None:
    scripted_input.set("")
    assert sd.configure_query_options(get_dataset("publicfiles_download"))["output_format"] == "raw"

def test_configure_export_options(scripted_input, tmp_path: Path) -> None:
    scripted_input.set(str(tmp_path / "out"), "y", "my name", "y", "n")

    assert sd.configure_export_options("gp", "json") == {
        "download_dir": tmp_path / "out",
        "custom_name": "my name",
        "overwrite": True,
        "pretty_json": False,
    }

def test_configure_export_options_defaults_non_json(scripted_input) -> None:
    scripted_input.set("", "", "")

    assert sd.configure_export_options("gp", "csv") == {
        "download_dir": Path("downloads"),
        "custom_name": None,
        "overwrite": False,
        "pretty_json": True,
    }

# =============================================================================
# execute_download_flow
# =============================================================================

def test_execute_download_flow_end_to_end(scripted_input, tmp_path: Path, capsys) -> None:
    client = FakeClient(ok_response())
    out_dir = tmp_path / "dl"
    scripted_input.set("", str(out_dir), "", "", "")

    sd.execute_download_flow(
        client=client,
        dataset=get_dataset("gp"),
        filters={"OBJECT_TYPE": "DEBRIS"},
        favorites=None,
        publicfiles_download_name=None,
        query_options=json_query_options(orderby="NORAD_CAT_ID", limit=5),
    )

    url, timeout = client.get_calls[0]
    assert url == (
        "https://www.space-track.org/basicspacedata/query/class/gp"
        "/OBJECT_TYPE/DEBRIS/orderby/NORAD_CAT_ID/limit/5/format/json"
    )
    assert timeout == 300

    files = sorted(p.name for p in out_dir.iterdir())
    assert len(files) == 2
    data_file = next(out_dir.glob("spacetrack_gp_*[0-9].json"))
    meta_file = data_file.with_name(data_file.stem + "_meta.json")
    assert meta_file.is_file()

    assert json.loads(data_file.read_text()) == [{"NORAD_CAT_ID": "25544"}]
    meta = json.loads(meta_file.read_text())
    assert meta["query_url"] == url
    assert meta["estimated_record_count"] == 1
    assert meta["response_status_code"] == 200
    assert "Done." in capsys.readouterr().out

def test_execute_download_flow_raw_format(scripted_input, tmp_path: Path) -> None:
    client = FakeClient(ok_response(text="", content=b"\x00\x01binary"))
    scripted_input.set("", str(tmp_path), "", "")

    sd.execute_download_flow(
        client=client,
        dataset=get_dataset("publicfiles_download"),
        filters={"name": "file.zip"},
        favorites=None,
        publicfiles_download_name="file.zip",
        query_options=json_query_options(output_format="raw"),
    )

    assert client.get_calls[0][0].endswith("/publicfiles/query/class/download?name=file.zip")
    assert (tmp_path / "file.zip").read_bytes() == b"\x00\x01binary"

def test_publicfiles_download_keeps_original_filename(scripted_input, tmp_path: Path) -> None:
    client = FakeClient(ok_response(text="", content=b"PK\x03\x04"))
    scripted_input.set("", str(tmp_path), "", "")

    sd.execute_download_flow(
        client=client,
        dataset=get_dataset("publicfiles_download"),
        filters={"name": "Report.zip"},
        favorites=None,
        publicfiles_download_name="Report.zip",
        query_options=json_query_options(output_format="raw"),
    )

    assert (tmp_path / "report.zip").is_file()

def test_publicfiles_download_custom_name_keeps_extension(scripted_input, tmp_path: Path) -> None:
    client = FakeClient(ok_response(text="", content=b"PK\x03\x04"))
    scripted_input.set("", str(tmp_path), "y", "my_report", "")

    sd.execute_download_flow(
        client=client,
        dataset=get_dataset("publicfiles_download"),
        filters={"name": "Data.zip"},
        favorites=None,
        publicfiles_download_name="Data.zip",
        query_options=json_query_options(output_format="raw"),
    )

    assert (tmp_path / "my_report.zip").read_bytes() == b"PK\x03\x04"

def test_execute_download_flow_cancelled(scripted_input, capsys) -> None:
    client = FakeClient(ok_response())
    scripted_input.set("n")

    sd.execute_download_flow(
        client=client,
        dataset=get_dataset("gp"),
        filters={},
        favorites=None,
        publicfiles_download_name=None,
        query_options=json_query_options(),
    )

    assert client.get_calls == []
    assert "Download cancelled." in capsys.readouterr().out

def test_execute_download_flow_query_builder_error(scripted_input, capsys) -> None:
    client = FakeClient(ok_response())

    sd.execute_download_flow(
        client=client,
        dataset=get_dataset("gp"),
        filters={"OBJECT_TYPE": ""},
        favorites=None,
        publicfiles_download_name=None,
        query_options=json_query_options(),
    )

    assert client.get_calls == []
    assert "Could not build query" in capsys.readouterr().out

@pytest.mark.parametrize(
    "error, message",
    [
        (SpaceTrackAuthenticationError("expired"), "Authentication error: expired"),
        (SpaceTrackRequestError("boom"), "Request failed: boom"),
        (SpaceTrackClientError("other"), "Space-Track client error: other"),
    ],
)
def test_execute_download_flow_client_errors(scripted_input, tmp_path: Path, capsys, error, message) -> None:
    scripted_input.set("", str(tmp_path), "", "", "")

    sd.execute_download_flow(
        client=FakeClient(error),
        dataset=get_dataset("gp"),
        filters={},
        favorites=None,
        publicfiles_download_name=None,
        query_options=json_query_options(),
    )

    assert message in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []

def test_execute_download_flow_export_failure_skips_metadata(monkeypatch, scripted_input, tmp_path: Path, capsys) -> None:
    metadata_calls: list[Any] = []

    def broken_export(**kwargs: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(downloader_core, "export_response", broken_export)
    monkeypatch.setattr(downloader_core, "save_metadata_for_export", lambda **kw: metadata_calls.append(kw))
    scripted_input.set("", str(tmp_path), "", "", "")

    sd.execute_download_flow(
        client=FakeClient(ok_response()),
        dataset=get_dataset("gp"),
        filters={},
        favorites=None,
        publicfiles_download_name=None,
        query_options=json_query_options(),
    )

    out = capsys.readouterr().out
    assert "Failed to export response: disk full" in out
    assert "Done." not in out
    assert metadata_calls == []

def test_execute_download_flow_metadata_failure_is_not_fatal(monkeypatch, scripted_input, tmp_path: Path, capsys) -> None:
    def broken_metadata(**kwargs: Any) -> None:
        raise RuntimeError("no metadata")

    monkeypatch.setattr(downloader_core, "save_metadata_for_export", broken_metadata)
    scripted_input.set("", str(tmp_path), "", "", "")

    sd.execute_download_flow(
        client=FakeClient(ok_response()),
        dataset=get_dataset("gp"),
        filters={},
        favorites=None,
        publicfiles_download_name=None,
        query_options=json_query_options(),
    )

    out = capsys.readouterr().out
    assert "metadata saving failed: no metadata" in out
    assert "Done." in out
    assert len(list(tmp_path.glob("*.json"))) == 1

def test_run_dataset_flow_wires_configuration_into_download(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    monkeypatch.setattr(
        sd,
        "configure_dataset_filters",
        lambda dataset: {"filters": {"A": "1"}, "favorites": "Weather", "publicfiles_download_name": None},
    )
    monkeypatch.setattr(sd, "configure_query_options", lambda dataset: {"output_format": "csv"})
    monkeypatch.setattr(sd, "execute_download_flow", lambda **kwargs: captured.update(kwargs))

    client = FakeClient()
    sd.run_dataset_flow(client, "satcat")

    assert captured["client"] is client
    assert captured["dataset"].key == "satcat"
    assert captured["filters"] == {"A": "1"}
    assert captured["favorites"] == "Weather"
    assert captured["query_options"] == {"output_format": "csv"}

def test_run_advanced_custom_query(monkeypatch, scripted_input) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(sd, "execute_download_flow", lambda **kwargs: captured.update(kwargs))
    scripted_input.set(
        menu_number(list(DATASETS), "boxscore"),
        "y", "country", "US", "",          # custom filters
        "", "", "", "", "", "", "",         # query options
    )

    sd.run_advanced_custom_query(FakeClient())

    assert captured["dataset"].key == "boxscore"
    assert captured["filters"] == {"COUNTRY": "US"}
    assert captured["favorites"] is None

# =============================================================================
# Main menu and entry point
# =============================================================================

MENU_KEYS = [key for key, _ in sd.dataset_group_options()]
QUIT = str(len(MENU_KEYS) + 1)

def test_main_menu_quit(scripted_input, capsys) -> None:
    scripted_input.set(QUIT)
    sd.run_main_menu(FakeClient())
    assert "Exiting." in capsys.readouterr().out

def test_main_menu_session_status(scripted_input) -> None:
    client = FakeClient()
    scripted_input.set(menu_number(MENU_KEYS, "session_status"), "", QUIT)

    sd.run_main_menu(client)

    assert client.status_checks == 1

def test_main_menu_back_and_dataset_selection(monkeypatch, scripted_input) -> None:
    flows: list[str] = []
    monkeypatch.setattr(sd, "run_dataset_flow", lambda client, key: flows.append(key))

    group_datasets = list(DATASET_GROUPS["object_elset"]["datasets"])
    back = str(len(group_datasets) + 1)
    group = menu_number(MENU_KEYS, "object_elset")

    scripted_input.set(group, back, group, menu_number(group_datasets, "gp_history"), "", QUIT)

    sd.run_main_menu(FakeClient())

    assert flows == ["gp_history"]

def test_main_menu_quit_from_dataset_menu(scripted_input) -> None:
    group_datasets = list(DATASET_GROUPS["catalog"]["datasets"])
    scripted_input.set(menu_number(MENU_KEYS, "catalog"), str(len(group_datasets) + 2))

    sd.run_main_menu(FakeClient())

def test_main_menu_advanced(monkeypatch, scripted_input) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(sd, "run_advanced_custom_query", calls.append)
    client = FakeClient()
    scripted_input.set(menu_number(MENU_KEYS, "advanced_custom"), "", QUIT)

    sd.run_main_menu(client)

    assert calls == [client]

def test_main_declined(monkeypatch, scripted_input) -> None:
    monkeypatch.setattr(sd, "create_logged_in_client", lambda **kw: pytest.fail("should not log in"))
    scripted_input.set("n")

    assert sd.main() == 0

def test_main_success_logs_out_and_closes(monkeypatch, scripted_input) -> None:
    client = FakeClient()
    login_kwargs: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> FakeClient:
        login_kwargs.update(kwargs)
        return client

    monkeypatch.setattr(sd, "create_logged_in_client", fake_create)
    monkeypatch.setattr(sd, "run_main_menu", lambda c: None)
    scripted_input.set("")

    assert sd.main() == 0
    assert login_kwargs == {"allow_prompt": True}
    assert client.logout_called and client.close_called

@pytest.mark.parametrize(
    "error, code",
    [
        (KeyboardInterrupt(), 130),
        (SpaceTrackAuthenticationError("bad"), 1),
        (SpaceTrackClientError("bad"), 1),
        (RuntimeError("bad"), 1),
    ],
)
def test_main_menu_errors_return_codes_and_clean_up(monkeypatch, scripted_input, error, code) -> None:
    client = FakeClient()

    def explode(c: FakeClient) -> None:
        raise error

    monkeypatch.setattr(sd, "create_logged_in_client", lambda **kw: client)
    monkeypatch.setattr(sd, "run_main_menu", explode)
    scripted_input.set("")

    assert sd.main() == code
    assert client.logout_called and client.close_called

def test_main_login_failure(monkeypatch, scripted_input, capsys) -> None:
    def fail(**kwargs: Any) -> None:
        raise SpaceTrackAuthenticationError("wrong password")

    monkeypatch.setattr(sd, "create_logged_in_client", fail)
    scripted_input.set("")

    assert sd.main() == 1
    assert "Authentication failed: wrong password" in capsys.readouterr().out

def test_main_skips_logout_when_session_already_ended(monkeypatch, scripted_input) -> None:
    client = FakeClient()
    client.logged_in = False
    monkeypatch.setattr(sd, "create_logged_in_client", lambda **kw: client)
    monkeypatch.setattr(sd, "run_main_menu", lambda c: None)
    scripted_input.set("")

    assert sd.main() == 0
    assert client.logout_called is False
    assert client.close_called is True
