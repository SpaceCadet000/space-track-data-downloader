# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         downloader_core.py
# PATH:         space-track-data-downloader/downloader_core.py
# AUTHOR:       Sooraj Suresh
# DATE:         October 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Prompt-free core shared by the terminal wizard and the web GUI:
#               declarative per-dataset filter specs, filter/query-option
#               assembly, the download pipeline stages, and download history.
#               Nothing here calls input() or prints.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dataset_configs import (
    COUNTRY_PRESETS,
    CREATION_DATE_RECENCY_FILTERS,
    DATASET_GROUPS,
    DATASETS,
    EPOCH_RECENCY_FILTERS,
    FAVORITES_PRESETS,
    FORMAT_DESCRIPTIONS,
    OBJECT_TYPE_FILTERS,
    ORBIT_REGIME_FILTERS,
    PREDICATE_DESCRIPTIONS,
    RCS_SIZE_FILTERS,
    dataset_uses_publicfiles_controller,
    get_common_filters,
    get_country_code,
    get_dataset,
    get_dataset_group,
    get_default_format,
    get_favorite_value,
    get_supported_formats,
    should_warn_legacy_tle,
    validate_dataset_format,
)
from exporters import (
    DEFAULT_DOWNLOAD_DIR,
    ExportResult,
    export_binary_response,
    export_public_file_bytes,
    export_response,
    make_text_preview,
)
from metadata import MetadataError, read_metadata_file, save_metadata_for_export
from query_builder import build_query_url, summarize_query
from spacetrack_client import SpaceTrackClient, SpaceTrackResponse

# =============================================================================
# Constants
# =============================================================================

NO_PREDICATE_FORMATS = frozenset({"tle", "3le", "raw"})
NO_METADATA_FORMATS = frozenset({"csv", "tle", "3le", "kvn"})
METADATA_SUFFIX = "_meta.json"

GP_HISTORY_WARNING = (
    "Historical GP queries can be very large. Use NORAD_CAT_ID and a "
    "short EPOCH or CREATION_DATE range whenever possible."
)
LEGACY_TLE_WARNING = (
    "TLE/3LE are legacy fixed-width formats. JSON, CSV, XML, or KVN "
    "are usually better for expanded catalog identifiers."
)
NULL_VALUE_HINT = (
    'Did you mean "null-val"? Space-Track matches empty fields with '
    'null-val; "null" matches nothing.'
)

NORAD_HELP = "Examples:\n  25544\n  25544,43013,48274\n  25544--26000\n  >40000\n  <100000"
NAME_HELP = "Examples:\n  ISS\n  STARLINK~~\n  OBJECT~~\n  COSMOS~~"
DATE_HELP = "Examples:\n  >now-7\n  2025-01-01--2025-01-31\n  >2025-01-01\n  <2025-12-31"
ORDERBY_HELP = "Examples:\n  NORAD_CAT_ID\n  EPOCH desc\n  CREATED desc\n  DECAY_EPOCH desc"
CUSTOM_FILTER_HELP = (
    "Add custom Space-Track REST filters one at a time.\n"
    "Examples:\n"
    "  Predicate: NORAD_CAT_ID      Value: 25544,43013\n"
    "  Predicate: EPOCH             Value: >now-30\n"
    "  Predicate: OBJECT_NAME       Value: STARLINK~~\n"
    "  Predicate: PERIOD            Value: 1430--1450\n"
    "  Predicate: DECAY_DATE        Value: null-val\n"
)
PRECEDENCE_HELP = (
    "PRECEDENCE examples:\n"
    "  4 = 60-day decay message\n"
    "  3 = TIP message\n"
    "  2 = Decay message\n"
    "  1 = SATCAT most recent decay date"
)
PUBLICFILE_HELP = (
    "To download a public file, first use:\n"
    "  Public files - detailed file metadata\n"
    "Then copy the LINK value into this prompt."
)

PRESET_TABLES: dict[str, dict[str, dict[str, Any]]] = {
    "object_type": OBJECT_TYPE_FILTERS,
    "orbit_regime": ORBIT_REGIME_FILTERS,
    "rcs_size": RCS_SIZE_FILTERS,
    "epoch_recency": EPOCH_RECENCY_FILTERS,
    "creation_date_recency": CREATION_DATE_RECENCY_FILTERS,
}

SATCAT_OBJECT_TYPES: tuple[tuple[str, str], ...] = (
    ("PAYLOAD", "PAYLOAD"),
    ("ROCKET BODY", "ROCKET BODY"),
    ("DEBRIS", "DEBRIS"),
    ("UNKNOWN", "UNKNOWN"),
)

# =============================================================================
# Exceptions
# =============================================================================

class CoreError(Exception):
    """
    Raised when GUI/CLI-supplied values cannot be turned into a valid query.
    """

# =============================================================================
# Menu option builders
# =============================================================================

def dataset_group_options() -> list[tuple[str, str]]:
    """
    Return dataset group menu options.
    """
    options: list[tuple[str, str]] = []

    for key, group in DATASET_GROUPS.items():
        label = f"{group['label']} - {group['description']}"
        options.append((key, label))

    options.append(("advanced_custom", "Advanced custom query builder"))
    options.append(("session_status", "Check Space-Track session status"))

    return options

def dataset_options_for_group(group_key: str) -> list[tuple[str, str]]:
    """
    Return dataset options for a selected group.
    """
    group = get_dataset_group(group_key)

    options: list[tuple[str, str]] = []

    for dataset_key in group["datasets"]:
        dataset = get_dataset(dataset_key)
        label = f"{dataset.label} - {dataset.description}"
        options.append((dataset.key, label))

    return options

def format_options_for_dataset(dataset_key: str) -> list[tuple[str, str]]:
    """
    Return output format options for a dataset.
    """
    return [
        (fmt, FORMAT_DESCRIPTIONS.get(fmt, fmt.upper()))
        for fmt in get_supported_formats(dataset_key)
    ]

def preset_options(table: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    """
    Return (key, "label - description") options for a preset filter table.
    """
    return [
        (key, f"{value['label']} - {value['description']}")
        for key, value in table.items()
    ]

def object_type_options() -> list[tuple[str, str]]:
    """
    Return object-type preset options.
    """
    return preset_options(OBJECT_TYPE_FILTERS)

def orbit_regime_options() -> list[tuple[str, str]]:
    """
    Return orbit-regime preset options.
    """
    return preset_options(ORBIT_REGIME_FILTERS)

def rcs_size_options() -> list[tuple[str, str]]:
    """
    Return RCS-size preset options.
    """
    return preset_options(RCS_SIZE_FILTERS)

def epoch_recency_options() -> list[tuple[str, str]]:
    """
    Return epoch-recency preset options.
    """
    return preset_options(EPOCH_RECENCY_FILTERS)

def creation_date_recency_options() -> list[tuple[str, str]]:
    """
    Return creation-date-recency preset options.
    """
    return preset_options(CREATION_DATE_RECENCY_FILTERS)

def country_options() -> list[tuple[str, str]]:
    """
    Return country preset options.
    """
    return [(key, value["label"]) for key, value in COUNTRY_PRESETS.items()]

def favorite_options() -> list[tuple[str, str]]:
    """
    Return favorites preset options.
    """
    return [(key, value["label"]) for key, value in FAVORITES_PRESETS.items()]

def predicate_options(dataset_key: str) -> list[tuple[str, str]]:
    """
    Return returned-predicate options for a dataset.
    """
    return [
        (
            predicate,
            f"{predicate} - {PREDICATE_DESCRIPTIONS.get(predicate, 'No description available')}",
        )
        for predicate in get_common_filters(dataset_key)
    ]

# =============================================================================
# Filter helpers
# =============================================================================

def merge_filters(
    base: dict[str, str],
    new_filters: dict[str, str],
) -> dict[str, str]:
    """
    Merge filters and return a new dictionary.

    New filters override existing filters.
    """
    merged = dict(base)
    merged.update(new_filters)
    return merged

def remove_empty_filters(filters: dict[str, str]) -> dict[str, str]:
    """
    Remove empty filter values.
    """
    return {
        predicate: value
        for predicate, value in filters.items()
        if str(value).strip() != ""
    }

def resolve_preset(table_name: str, option_key: str) -> dict[str, str]:
    """
    Return the filters of one preset-table option.
    """
    try:
        table = PRESET_TABLES[table_name]
    except KeyError as exc:
        raise CoreError(f"Unknown preset table: {table_name!r}") from exc

    if option_key not in table:
        raise CoreError(f"Unknown {table_name} option: {option_key!r}")

    return dict(table[option_key]["filters"])

def resolve_country(
    predicate_name: str,
    option_key: str,
    custom_code: str | None = None,
) -> dict[str, str]:
    """
    Return a country/owner filter for a preset key.

    The "custom" preset uses custom_code, upper-cased.
    """
    try:
        value = get_country_code(option_key)
    except KeyError as exc:
        raise CoreError(f"Unknown country option: {option_key!r}") from exc

    if value is None:
        return {}

    if value == "custom":
        code = (custom_code or "").strip().upper()

        if not code:
            raise CoreError("A custom country/owner code is required.")

        return {predicate_name: code}

    return {predicate_name: value}

def resolve_favorites(option_key: str) -> str:
    """
    Return the Space-Track favorites value for a preset key.
    """
    try:
        return get_favorite_value(option_key)
    except KeyError as exc:
        raise CoreError(f"Unknown favorites option: {option_key!r}") from exc

def normalize_custom_filters(raw: Any) -> dict[str, str]:
    """
    Normalize custom predicate/value filters.

    Accepts a dict or a list of [predicate, value] pairs. Predicates are
    upper-cased; later duplicates win, like repeated CLI entries.
    """
    if raw is None:
        return {}

    pairs: list[Any]

    if isinstance(raw, dict):
        pairs = list(raw.items())
    elif isinstance(raw, (list, tuple)):
        pairs = list(raw)
    else:
        raise CoreError("Custom filters must be a mapping or a list of pairs.")

    filters: dict[str, str] = {}

    for pair in pairs:
        if isinstance(pair, dict):
            pair = (pair.get("predicate"), pair.get("value"))

        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise CoreError("Each custom filter must be a predicate/value pair.")

        predicate = str(pair[0] or "").strip().upper()
        value = str(pair[1] if pair[1] is not None else "").strip()

        if not predicate and not value:
            continue

        if not predicate or not value:
            raise CoreError("Custom filters need both a predicate and a value.")

        filters[predicate] = value

    return filters

# =============================================================================
# Declarative filter specs
# =============================================================================

@dataclass(frozen=True)
class FilterField:
    """
    One question in a dataset's filter wizard.

    Attributes:
        id:
            Stable key used in the values mapping.

        kind:
            preset, country, choice, text, date, flag, favorites, or custom.

        label:
            Title for menus, or the value prompt for text/date fields.

        predicate:
            Space-Track predicate written by text/date/choice/flag/country.

        gate:
            Yes/no question asked before the field, or None if always asked.

        gate_default:
            Default answer to the gate question.

        default:
            Default preset key, choice key, or text value.

        value:
            Fixed value written by a flag field.

        options:
            (key, label) choices for choice fields.

        preset_table:
            PRESET_TABLES key for preset fields.

        help:
            Examples shown before the value prompt.

        uppercase:
            Whether text input is upper-cased.
    """

    id: str
    kind: str
    label: str
    predicate: str | None = None
    gate: str | None = None
    gate_default: bool = False
    default: str | None = None
    value: str | None = None
    options: tuple[tuple[str, str], ...] = ()
    preset_table: str | None = None
    help: str | None = None
    uppercase: bool = False

    def choices(self) -> list[tuple[str, str]]:
        """
        Return the menu choices for preset/country/choice/favorites fields.
        """
        if self.kind == "preset" and self.preset_table:
            return preset_options(PRESET_TABLES[self.preset_table])

        if self.kind == "country":
            return country_options()

        if self.kind == "favorites":
            return favorite_options()

        return list(self.options)

def _preset(field_id: str, table: str, label: str, gate: str | None = None, gate_default: bool = False, default: str = "all") -> FilterField:
    return FilterField(field_id, "preset", label, gate=gate, gate_default=gate_default, default=default, preset_table=table)

def country_field(predicate: str, gate: str | None = None) -> FilterField:
    return FilterField("country", "country", "Country / owner filter", predicate=predicate, gate=gate, default="all")

def norad_field() -> FilterField:
    return FilterField(
        "norad", "text", "NORAD_CAT_ID value", predicate="NORAD_CAT_ID",
        gate="Filter by NORAD catalog ID, comma list, or range?", help=NORAD_HELP,
    )

def name_field(predicate: str) -> FilterField:
    return FilterField(
        "name", "text", f"{predicate} value", predicate=predicate,
        gate=f"Filter by {predicate} wildcard/name?", help=NAME_HELP,
    )

def date_field(field_id: str, predicate: str, gate: str, gate_default: bool = False, default: str | None = None) -> FilterField:
    return FilterField(
        field_id, "date", f"{predicate} value", predicate=predicate,
        gate=gate, gate_default=gate_default, default=default, help=DATE_HELP,
    )

def _text(field_id: str, predicate: str, label: str, gate: str, *, gate_default: bool = False, default: str | None = None, help: str | None = None, uppercase: bool = False) -> FilterField:
    return FilterField(
        field_id, "text", label, predicate=predicate, gate=gate,
        gate_default=gate_default, default=default, help=help, uppercase=uppercase,
    )

def _flag(field_id: str, predicate: str, value: str, gate: str, gate_default: bool = False) -> FilterField:
    return FilterField(field_id, "flag", gate, predicate=predicate, gate=gate, gate_default=gate_default, value=value)

CUSTOM_FIELD = FilterField(
    "custom", "custom", "Advanced custom predicate/value filters",
    gate="Add advanced custom predicate/value filters?", help=CUSTOM_FILTER_HELP,
)
FAVORITES_FIELD = FilterField(
    "favorites", "favorites", "Favorites list",
    gate="Filter by Space-Track favorites list?", default="geosynchronous",
)

def _gp_fields(dataset_key: str) -> list[FilterField]:
    fields: list[FilterField] = []

    if dataset_key == "gp":
        fields.append(_preset("object_type", "object_type", "Object type / object population", default="all_on_orbit"))
    else:
        # gp_history asks for NORAD_CAT_ID first, right after its size warning.
        fields.append(norad_field())

    fields += [
        _preset("orbit_regime", "orbit_regime", "Orbit regime filter", gate="Configure orbit-regime filter?", gate_default=True),
        _preset("rcs_size", "rcs_size", "Radar cross-section size filter", gate="Configure RCS-size filter?"),
        _preset("epoch_recency", "epoch_recency", "EPOCH recency filter", gate="Configure EPOCH recency filter?", gate_default=True),
        _preset("creation_date_recency", "creation_date_recency", "CREATION_DATE recency filter", gate="Configure CREATION_DATE recency filter?"),
        country_field("COUNTRY_CODE"),
    ]

    if dataset_key == "gp":
        fields.append(norad_field())

    fields += [
        name_field("OBJECT_NAME"),
        _text("site", "SITE", "SITE value, for example AFETR, TTMTR, FRGUI", "Filter by launch site SITE?", uppercase=True),
        date_field("launch_date", "LAUNCH_DATE", "Filter by LAUNCH_DATE?"),
        CUSTOM_FIELD,
        FAVORITES_FIELD,
    ]

    return fields

def _satcat_fields(dataset_key: str) -> list[FilterField]:
    dataset = get_dataset(dataset_key)

    if dataset_key == "satcat":
        fields = [
            _flag("current", "CURRENT", "Y", "Use only current SATCAT records?", gate_default=True),
            _flag("on_orbit", "DECAY", "null-val", "Filter by on-orbit only using DECAY/null-val?"),
            FilterField(
                "object_type", "choice", "SATCAT object type", predicate="OBJECT_TYPE",
                gate="Filter by object type?", default="PAYLOAD", options=SATCAT_OBJECT_TYPES,
            ),
            country_field("COUNTRY"),
            date_field("launch", "LAUNCH", "Filter by launch date LAUNCH?"),
            date_field("decay", "DECAY", "Filter by decay date DECAY?"),
            _text("site", "SITE", "SITE value", "Filter by launch site SITE?", uppercase=True),
            norad_field(),
            name_field("SATNAME"),
        ]

    elif dataset_key == "satcat_debut":
        fields = [
            _text("debut", "DEBUT", "DEBUT value", "Use recent DEBUT filter?", gate_default=True, default=">now-1"),
            norad_field(),
            name_field("SATNAME"),
            country_field("COUNTRY"),
        ]

    elif dataset_key == "satcat_change":
        fields = [
            date_field(
                "change_date", "CHANGE_DATE", "Filter by CHANGE_DATE?", gate_default=True,
                default=dataset.recommended_filters.get("CHANGE_DATE", ">now-7"),
            ),
            norad_field(),
            name_field("SATNAME"),
            country_field("COUNTRY"),
        ]

    else:  # launch_site
        fields = [
            _text("site_code", "SITE_CODE", "SITE_CODE", "Filter by SITE_CODE?", uppercase=True),
            _text("launch_site", "LAUNCH_SITE", "LAUNCH_SITE value, for example CAPE~~", "Filter by LAUNCH_SITE wildcard/name?"),
        ]

    return fields + [CUSTOM_FIELD]

def _decay_fields(dataset_key: str) -> list[FilterField]:
    dataset = get_dataset(dataset_key)
    fields = [norad_field()]

    if dataset_key == "decay":
        fields += [
            date_field("msg_epoch", "MSG_EPOCH", "Filter by MSG_EPOCH?"),
            date_field(
                "decay_epoch", "DECAY_EPOCH", "Filter by DECAY_EPOCH?", gate_default=True,
                default=dataset.recommended_filters.get("DECAY_EPOCH", ">now-7"),
            ),
            name_field("OBJECT_NAME"),
            country_field("COUNTRY_CODE"),
            _preset("rcs_size", "rcs_size", "Radar cross-section size filter", gate="Filter by RCS_SIZE?"),
            _text("precedence", "PRECEDENCE", "PRECEDENCE value", "Filter by PRECEDENCE?", help=PRECEDENCE_HELP),
        ]

    else:  # tip
        fields += [
            date_field(
                "insert_epoch", "INSERT_EPOCH", "Filter by INSERT_EPOCH?", gate_default=True,
                default=dataset.recommended_filters.get("INSERT_EPOCH", ">now-7"),
            ),
            date_field("msg_epoch", "MSG_EPOCH", "Filter by MSG_EPOCH?"),
            date_field("decay_epoch", "DECAY_EPOCH", "Filter by DECAY_EPOCH?"),
            _flag("high_interest", "HIGH_INTEREST", "Y", "Filter high-interest TIPs only?"),
        ]

    return fields + [CUSTOM_FIELD]

def _cdm_fields(dataset_key: str) -> list[FilterField]:
    dataset = get_dataset(dataset_key)

    return [
        date_field(
            "created", "CREATED", "Filter by CREATED date?", gate_default=True,
            default=dataset.recommended_filters.get("CREATED", ">now-7"),
        ),
        date_field("tca", "TCA", "Filter by TCA date?"),
        _text("sat_1_id", "SAT_1_ID", "SAT_1_ID value", "Filter by SAT_1_ID?"),
        _text("sat_2_id", "SAT_2_ID", "SAT_2_ID value", "Filter by SAT_2_ID?"),
        _flag("emergency", "EMERGENCY_REPORTABLE", "Y", "Emergency-reportable only?"),
        _text("pc", "PC", "PC value, for example >0.00001", "Filter by minimum collision probability PC?"),
        _text("min_rng", "MIN_RNG", "MIN_RNG value, for example <5", "Filter by maximum MIN_RNG?"),
        CUSTOM_FIELD,
    ]

def _publicfiles_fields(dataset_key: str) -> list[FilterField]:
    if dataset_key != "publicfiles_download":
        return []

    return [
        FilterField(
            "publicfile_name", "text", "Public file LINK/name value",
            predicate="name", help=PUBLICFILE_HELP,
        ),
    ]

def dataset_flow(dataset_key: str) -> str:
    """
    Return the name of the wizard flow a dataset uses.
    """
    if dataset_key in {"gp", "gp_history"}:
        return "gp_like"

    if dataset_key in {"satcat", "satcat_change", "satcat_debut", "launch_site"}:
        return "satcat"

    if dataset_key in {"decay", "tip"}:
        return "decay"

    if dataset_key == "cdm_public":
        return "cdm"

    if dataset_key == "boxscore":
        return "boxscore"

    if dataset_uses_publicfiles_controller(dataset_key):
        return "publicfiles"

    return "generic"

def dataset_filter_fields(dataset_key: str) -> list[FilterField]:
    """
    Return the ordered filter questions for a dataset.

    The order is the order the terminal wizard asks them in.
    """
    get_dataset(dataset_key)
    flow = dataset_flow(dataset_key)

    if flow == "gp_like":
        return _gp_fields(dataset_key)

    if flow == "satcat":
        return _satcat_fields(dataset_key)

    if flow == "decay":
        return _decay_fields(dataset_key)

    if flow == "cdm":
        return _cdm_fields(dataset_key)

    if flow == "boxscore":
        return [country_field("COUNTRY", gate="Filter by country?"), CUSTOM_FIELD]

    if flow == "publicfiles":
        return _publicfiles_fields(dataset_key)

    return [CUSTOM_FIELD]

def dataset_warning(dataset_key: str) -> str | None:
    """
    Return a dataset-level warning shown before its filters, if any.
    """
    return GP_HISTORY_WARNING if dataset_key == "gp_history" else None

def default_filter_values(dataset_key: str) -> dict[str, Any]:
    """
    Return the values the terminal wizard produces when every prompt is
    answered with Enter (gates left at their defaults).
    """
    values: dict[str, Any] = {}

    for spec in dataset_filter_fields(dataset_key):
        if spec.gate is not None and not spec.gate_default:
            continue

        if spec.kind == "flag":
            values[spec.id] = True

        elif spec.kind in {"preset", "country", "choice", "favorites", "text", "date"} and spec.default is not None:
            values[spec.id] = spec.default

    return values

def resolve_field(spec: FilterField, value: Any) -> dict[str, str]:
    """
    Turn one field's value into Space-Track filters.

    Favorites and custom fields are handled by build_filter_config.
    """
    if spec.kind == "preset":
        return resolve_preset(str(spec.preset_table), str(value))

    if spec.kind == "country":
        if isinstance(value, dict):
            return resolve_country(str(spec.predicate), str(value.get("preset", "all")), value.get("custom"))

        return resolve_country(str(spec.predicate), str(value))

    if spec.kind == "choice":
        keys = {key for key, _ in spec.options}

        if str(value) not in keys:
            raise CoreError(f"Unknown {spec.label} option: {value!r}")

        return {str(spec.predicate): str(value)}

    if spec.kind == "flag":
        return {str(spec.predicate): str(spec.value)} if value else {}

    if spec.kind in {"text", "date"}:
        text = str(value if value is not None else "").strip()

        if spec.uppercase:
            text = text.upper()

        return {str(spec.predicate): text}

    if spec.kind == "custom":
        return normalize_custom_filters(value)

    raise CoreError(f"Field {spec.id!r} of kind {spec.kind!r} has no filters.")

def build_filter_config(
    dataset_key: str,
    values: dict[str, Any] | None,
    fields: list[FilterField] | None = None,
) -> dict[str, Any]:
    """
    Build the filter configuration for a dataset from field values.

    Args:
        dataset_key:
            Dataset key.

        values:
            Mapping of FilterField.id to value. A missing or None value means
            the field is off (gate answered "no"); ungated preset/country
            fields fall back to their default.

        fields:
            Field specs to use instead of the dataset's own.

    Returns:
        {"filters", "favorites"} plus "publicfiles_download_name" for
        publicfiles datasets, matching the terminal wizard's result.
    """
    values = dict(values or {})
    specs = dataset_filter_fields(dataset_key) if fields is None else fields
    known = {spec.id for spec in specs}
    unknown = sorted(set(values) - known)

    if unknown:
        raise CoreError(f"Unknown filter fields for {dataset_key}: {', '.join(unknown)}")

    filters: dict[str, str] = {}
    favorites: str | None = None
    publicfiles_download_name: str | None = None

    for spec in specs:
        value = values.get(spec.id)

        if value is None and spec.gate is None and spec.kind in {"preset", "country"}:
            value = spec.default

        if value is None or value is False:
            continue

        if spec.kind == "favorites":
            favorites = resolve_favorites(str(value))
            continue

        new_filters = resolve_field(spec, value)

        if spec.id == "publicfile_name":
            publicfiles_download_name = new_filters.get("name") or None

        filters = merge_filters(filters, new_filters)

    config: dict[str, Any] = {
        "filters": remove_empty_filters(filters),
        "favorites": favorites,
    }

    if dataset_flow(dataset_key) == "publicfiles":
        config["publicfiles_download_name"] = publicfiles_download_name

    return config

def null_value_hints(values: dict[str, Any] | None) -> list[dict[str, Any]]:
    """
    Point out filter values typed as "null" where Space-Track expects "null-val".

    The values are left as they are; "null" is a valid (if empty-handed) value.

    Args:
        values:
            The same field-id mapping build_filter_config takes.

    Returns:
        One {"field", "message"} per suspect text value, plus "index" (the
        position among the custom pairs) for custom filter values.
    """
    hints: list[dict[str, Any]] = []

    def is_null(value: Any) -> bool:
        return isinstance(value, str) and value.strip().lower() == "null"

    for field_id, value in (values or {}).items():
        if is_null(value):
            hints.append({"field": field_id, "message": NULL_VALUE_HINT})

        elif isinstance(value, (list, tuple)):
            for index, pair in enumerate(value):
                if isinstance(pair, (list, tuple)) and len(pair) == 2 and is_null(pair[1]):
                    hints.append({"field": field_id, "index": index, "message": NULL_VALUE_HINT})

    return hints

# =============================================================================
# Query options
# =============================================================================

def format_warning(dataset_key: str, output_format: str) -> str | None:
    """
    Return the legacy-format warning for TLE/3LE, if it applies.
    """
    return LEGACY_TLE_WARNING if should_warn_legacy_tle(dataset_key, output_format) else None

def query_option_availability(dataset_key: str, output_format: str) -> dict[str, bool]:
    """
    Return which query-level options apply to a dataset and format.
    """
    fmt = output_format.lower().strip()
    basic = not dataset_uses_publicfiles_controller(dataset_key)

    return {
        "predicates": fmt not in NO_PREDICATE_FORMATS,
        "orderby": basic,
        "limit": basic,
        "offset": basic,
        "metadata": basic and fmt not in NO_METADATA_FORMATS,
        "show_empty": basic,
        "distinct": basic,
    }

def _optional_int(value: Any, name: str, minimum: int) -> int | None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None

    if isinstance(value, bool):
        raise CoreError(f"{name} must be an integer.")

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise CoreError(f"{name} must be an integer.") from exc

    if number < minimum:
        raise CoreError(f"{name} must be >= {minimum}.")

    return number

def normalize_query_options(dataset_key: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    """
    Validate query options and drop the ones that don't apply.

    Returns the same keys configure_query_options returns.
    """
    raw = dict(raw or {})
    output_format = str(raw.get("output_format") or get_default_format(dataset_key)).lower().strip()

    try:
        validate_dataset_format(dataset_key, output_format)
    except (KeyError, ValueError) as exc:
        raise CoreError(str(exc)) from exc

    available = query_option_availability(dataset_key, output_format)

    predicates = None

    if available["predicates"] and raw.get("predicates"):
        items = raw["predicates"]

        if isinstance(items, str):
            items = items.split(",")

        predicates = [str(item).strip() for item in items if str(item).strip()] or None

    orderby = None
    limit = None
    offset = None

    if available["orderby"]:
        orderby = str(raw.get("orderby") or "").strip() or None

    if available["limit"]:
        limit = _optional_int(raw.get("limit"), "limit", 1)
        offset = _optional_int(raw.get("offset"), "offset", 0)

        if offset is not None and limit is None:
            raise CoreError("An offset needs a limit.")

    return {
        "output_format": output_format,
        "predicates": predicates,
        "orderby": orderby,
        "limit": limit,
        "offset": offset,
        "metadata": bool(raw.get("metadata", False)) and available["metadata"],
        "show_empty": bool(raw.get("show_empty", True)) and available["show_empty"],
        "distinct": bool(raw.get("distinct", False)) and available["distinct"],
    }

def default_query_options(dataset_key: str) -> dict[str, Any]:
    """
    Return the query options the terminal wizard produces on all-Enter.
    """
    dataset = get_dataset(dataset_key)
    return normalize_query_options(dataset_key, {"orderby": dataset.default_orderby})

# =============================================================================
# Query preparation
# =============================================================================

@dataclass(frozen=True)
class PreparedQuery:
    """
    A built query URL and its summary (which feeds metadata).
    """

    dataset_key: str
    url: str
    summary: dict[str, Any]
    output_format: str
    publicfiles_download_name: str | None = None

def prepare_query(
    *,
    dataset_key: str,
    filters: dict[str, str],
    favorites: str | None,
    publicfiles_download_name: str | None,
    query_options: dict[str, Any],
) -> PreparedQuery:
    """
    Build the query URL and summary with identical arguments.

    Raises:
        QueryBuilderError: If the query is invalid.
    """
    output_format = query_options["output_format"]
    kwargs: dict[str, Any] = {
        "dataset_key": dataset_key,
        "filters": filters,
        "output_format": output_format,
        "predicates": query_options.get("predicates"),
        "orderby": query_options.get("orderby"),
        "limit": query_options.get("limit"),
        "offset": query_options.get("offset"),
        "metadata": query_options.get("metadata", False),
        "show_empty": query_options.get("show_empty", False),
        "favorites": favorites,
        "distinct": query_options.get("distinct", False),
        "publicfiles_download_name": publicfiles_download_name,
        "use_recommended_filters": False,
    }

    return PreparedQuery(
        dataset_key=dataset_key,
        url=build_query_url(**kwargs),
        summary=summarize_query(**kwargs),
        output_format=output_format,
        publicfiles_download_name=publicfiles_download_name,
    )

# =============================================================================
# Download pipeline stages
# =============================================================================

def fetch(client: SpaceTrackClient, url: str) -> SpaceTrackResponse:
    """
    Send the download request. This is the only stage that touches the network.
    """
    return client.get(url, timeout_seconds=client.download_timeout_seconds)

def public_file_output_name(custom_name: str | None, link_name: str | None) -> str:
    """
    Return the file name for a public-file download.

    A custom name is a base without extension, so it keeps the file's own.
    """
    name = custom_name or link_name or "space_track_public_file"

    if custom_name and not Path(name).suffix:
        name += Path(link_name or "").suffix

    return name

def export_download(
    *,
    response: SpaceTrackResponse,
    dataset_key: str,
    output_format: str,
    publicfiles_download_name: str | None,
    export_options: dict[str, Any],
    print_preview: bool = False,
) -> ExportResult:
    """
    Save a response with the right exporter.
    """
    # Checked before the generic raw branch: publicfiles_download is
    # always raw, and should keep its original file name.
    if dataset_key == "publicfiles_download":
        return export_public_file_bytes(
            content=response.content,
            original_name=public_file_output_name(export_options["custom_name"], publicfiles_download_name),
            download_dir=export_options["download_dir"],
            overwrite=export_options["overwrite"],
            print_preview=print_preview,
        )

    if output_format == "raw":
        return export_binary_response(
            content=response.content,
            dataset_key=dataset_key,
            output_format="raw",
            download_dir=export_options["download_dir"],
            custom_name=export_options["custom_name"],
            overwrite=export_options["overwrite"],
            print_preview=print_preview,
        )

    return export_response(
        content=response.text,
        dataset_key=dataset_key,
        output_format=output_format,
        download_dir=export_options["download_dir"],
        custom_name=export_options["custom_name"],
        overwrite=export_options["overwrite"],
        pretty_json=export_options["pretty_json"],
        print_preview=print_preview,
    )

def save_download_metadata(
    *,
    prepared: PreparedQuery,
    export_result: ExportResult,
    response: SpaceTrackResponse,
    overwrite: bool,
    print_summary: bool = False,
) -> Path:
    """
    Write the _meta.json sidecar for an export.
    """
    return save_metadata_for_export(
        query_summary=prepared.summary,
        export_result=export_result,
        response_status_code=response.status_code,
        response_elapsed_seconds=response.elapsed_seconds,
        response_headers=response.headers,
        overwrite=overwrite,
        print_summary=print_summary,
    )

def resolve_download_dir(raw: str | Path | None, base_dir: str | Path = DEFAULT_DOWNLOAD_DIR) -> Path:
    """
    Resolve a download directory that must stay inside base_dir.

    Relative paths are taken relative to base_dir; a path that already
    starts with base_dir is accepted as-is.
    """
    base = Path(base_dir)
    base_resolved = base.resolve()
    text = str(raw or "").strip()

    if not text:
        return base

    candidate = Path(text)

    if not candidate.is_absolute() and candidate.parts[: len(base.parts)] != base.parts:
        candidate = base / candidate

    resolved = candidate.resolve()

    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise CoreError(f"Download directory must be inside {base}/.")

    return candidate

# =============================================================================
# Output previews and history
# =============================================================================

PREVIEW_ROWS = 50
PREVIEW_PARSE_LIMIT_BYTES = 5 * 1024 * 1024

def _ensure_inside(path: Path, base_dir: Path) -> Path:
    resolved = path.resolve()
    base = base_dir.resolve()

    if resolved != base and base not in resolved.parents:
        raise CoreError("File is outside the download directory.")

    return resolved

def table_preview(text: str, output_format: str, max_rows: int = PREVIEW_ROWS) -> dict[str, Any] | None:
    """
    Return {"columns", "rows", "total"} for JSON lists of objects or CSV.
    """
    fmt = output_format.lower()

    if fmt == "json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        if isinstance(data, dict) and isinstance(data.get("data"), list):
            data = data["data"]

        if not isinstance(data, list) or not data or not all(isinstance(row, dict) for row in data):
            return None

        columns: list[str] = []

        for row in data[:max_rows]:
            for key in row:
                if key not in columns:
                    columns.append(str(key))

        rows = [[_cell(row.get(col)) for col in columns] for row in data[:max_rows]]
        return {"columns": columns, "rows": rows, "total": len(data)}

    if fmt == "csv":
        reader = csv.reader(io.StringIO(text))
        all_rows = [row for row in reader if row]

        if not all_rows:
            return None

        return {"columns": all_rows[0], "rows": all_rows[1 : max_rows + 1], "total": len(all_rows) - 1}

    return None

def _cell(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        return json.dumps(value)

    return str(value)

def read_output_preview(
    path: str | Path,
    output_format: str,
    base_dir: str | Path = DEFAULT_DOWNLOAD_DIR,
) -> dict[str, Any]:
    """
    Read a saved output file for display.

    Raises:
        CoreError: If the file is outside base_dir or missing.
    """
    resolved = _ensure_inside(Path(path), Path(base_dir))

    if not resolved.is_file():
        raise CoreError("Output file no longer exists.")

    size = resolved.stat().st_size
    fmt = (output_format or "").lower()

    if fmt == "raw" or size > PREVIEW_PARSE_LIMIT_BYTES:
        with resolved.open("rb") as handle:
            head = handle.read(64 * 1024)

        text = make_text_preview(head, fmt if fmt == "raw" else "text", max_lines=40)
        return {"text": text, "table": None, "size_bytes": size, "truncated": size > len(head)}

    content = resolved.read_text(encoding="utf-8", errors="replace")

    return {
        "text": make_text_preview(content, fmt, max_lines=40, max_chars=8000),
        "table": table_preview(content, fmt),
        "size_bytes": size,
        "truncated": False,
    }

@dataclass
class HistoryListing:
    """
    Download history entries plus files that could not be read.
    """

    entries: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

def history_entry(meta_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """
    Trim a metadata dictionary to what the history view needs.
    """
    output_file = str(data.get("output_file") or "")

    return {
        "meta_file": str(meta_path),
        "created_utc": data.get("created_utc"),
        "dataset_key": data.get("dataset_key"),
        "dataset_label": data.get("dataset_label"),
        "output_format": data.get("output_format"),
        "query_url": data.get("query_url"),
        "filters": data.get("filters") or {},
        "predicates": data.get("predicates"),
        "orderby": data.get("orderby"),
        "limit": data.get("limit"),
        "favorites": data.get("favorites"),
        "output_file": output_file,
        "output_filename": data.get("output_filename"),
        "output_size_bytes": data.get("output_size_bytes"),
        "estimated_record_count": data.get("estimated_record_count"),
        "response_status_code": data.get("response_status_code"),
        "response_elapsed_seconds": data.get("response_elapsed_seconds"),
        "notes": data.get("notes") or [],
        "output_exists": bool(output_file) and Path(output_file).is_file(),
    }

def list_download_history(download_dir: str | Path = DEFAULT_DOWNLOAD_DIR) -> HistoryListing:
    """
    Read every *_meta.json under download_dir, newest first.

    Unreadable sidecars are reported in errors, not raised.
    """
    listing = HistoryListing()
    base = Path(download_dir)

    if not base.is_dir():
        return listing

    for meta_path in sorted(base.rglob(f"*{METADATA_SUFFIX}")):
        try:
            data = read_metadata_file(meta_path)
        except MetadataError as exc:
            listing.errors.append(str(exc))
            continue

        if "query_url" not in data or "dataset_key" not in data:
            listing.errors.append(f"Not a download metadata file: {meta_path}")
            continue

        listing.entries.append(history_entry(meta_path, data))

    listing.entries.sort(key=lambda entry: str(entry.get("created_utc") or ""), reverse=True)
    return listing

# =============================================================================
# Catalog description (for the GUI)
# =============================================================================

def describe_field(spec: FilterField) -> dict[str, Any]:
    """
    Return a JSON-friendly description of one filter field.
    """
    return {
        "id": spec.id,
        "kind": spec.kind,
        "label": spec.label,
        "predicate": spec.predicate,
        "gate": spec.gate,
        "gate_default": spec.gate_default,
        "default": spec.default,
        "value": spec.value,
        "options": [{"key": key, "label": label} for key, label in spec.choices()],
        "help": spec.help,
        "uppercase": spec.uppercase,
    }

def describe_dataset(dataset_key: str) -> dict[str, Any]:
    """
    Return a JSON-friendly description of a dataset, its fields and options.
    """
    dataset = get_dataset(dataset_key)

    return {
        "key": dataset.key,
        "label": dataset.label,
        "description": dataset.description,
        "controller": dataset.controller,
        "api_class": dataset.api_class,
        "default_format": dataset.default_format,
        "formats": [
            {
                "key": fmt,
                "label": label,
                "warning": format_warning(dataset_key, fmt),
                "options": query_option_availability(dataset_key, fmt),
            }
            for fmt, label in format_options_for_dataset(dataset_key)
        ],
        "default_orderby": dataset.default_orderby,
        "notes": list(dataset.notes),
        "warning": dataset_warning(dataset_key),
        "fields": [describe_field(spec) for spec in dataset_filter_fields(dataset_key)],
        "default_values": default_filter_values(dataset_key),
        "predicate_options": [{"key": key, "label": label} for key, label in predicate_options(dataset_key)],
        "orderby_help": ORDERBY_HELP,
    }

def dataset_catalog() -> list[dict[str, Any]]:
    """
    Return dataset groups with brief dataset entries.
    """
    groups = []

    for group_key, group in DATASET_GROUPS.items():
        datasets = []

        for dataset_key in group["datasets"]:
            dataset = DATASETS[dataset_key]
            datasets.append(
                {
                    "key": dataset.key,
                    "label": dataset.label,
                    "description": dataset.description,
                    "controller": dataset.controller,
                    "api_class": dataset.api_class,
                    "default_format": dataset.default_format,
                    "formats": list(dataset.supported_formats),
                    "warning": dataset_warning(dataset.key),
                }
            )

        groups.append(
            {
                "key": group_key,
                "label": group["label"],
                "description": group["description"],
                "datasets": datasets,
            }
        )

    return groups
