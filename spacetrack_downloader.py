# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ███████╗██████╗  █████╗  ██████╗███████╗      ████████╗██████╗  █████╗  ██████╗██╗  ██╗
#  ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔════╝      ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝
#  ███████╗██████╔╝███████║██║     █████╗           ██║   ██████╔╝███████║██║     █████╔╝
#  ╚════██║██╔═══╝ ██╔══██║██║     ██╔══╝           ██║   ██╔══██╗██╔══██║██║     ██╔═██╗
#  ███████║██║     ██║  ██║╚██████╗███████╗         ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗
#  ╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝         ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT NAME: Space-Track Data Downloader
# FILE:         spacetrack_downloader.py
# PATH:         space-track-data-downloader/spacetrack_downloader.py
# AUTHOR:       Sooraj Suresh
# DATE:         May 2026
# VERSION:      1.0.0
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DESCRIPTION:  Provides the main interactive command-line interface for selecting datasets, 
#               configuring filters, downloading data, and saving outputs.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from __future__ import annotations
import sys
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
    DatasetConfig,
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
)
from metadata import save_metadata_for_export
from query_builder import (
    QueryBuilderError,
    build_query_url,
    print_query_summary,
    summarize_query,
)
from spacetrack_client import (
    SpaceTrackAuthenticationError,
    SpaceTrackClient,
    SpaceTrackClientError,
    SpaceTrackRequestError,
    create_logged_in_client,
)

APP_NAME = "Space-Track Data Downloader"
APP_VERSION = "1.0.0"

# =============================================================================
# Terminal display helpers
# =============================================================================

def print_header(title: str) -> None:
    """
    Print a large section header.
    """
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)

def print_subheader(title: str) -> None:
    """
    Print a smaller section header.
    """
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)

def print_app_banner() -> None:
    """
    Print the application banner.
    """
    print_header(f"{APP_NAME} v{APP_VERSION}")
    print(
        "Interactive downloader and query builder for Space-Track.org data.\n"
        "This tool builds official REST-style Space-Track API URLs and saves\n"
        "the downloaded response plus metadata."
    )

def print_warning(message: str) -> None:
    """
    Print a warning message.
    """
    print(f"\n[!] {message}")

def print_info(message: str) -> None:
    """
    Print an informational message.
    """
    print(f"[*] {message}")

def print_success(message: str) -> None:
    """
    Print a success message.
    """
    print(f"[+] {message}")


# =============================================================================
# Input helpers
# =============================================================================

def prompt_enter_to_continue() -> None:
    """
    Wait for the user to press Enter.
    """
    input("\nPress Enter to continue...")

def prompt_text(
    prompt: str,
    *,
    default: str | None = None,
    allow_empty: bool = False,
) -> str:
    """
    Prompt for a text value.

    Args:
        prompt:
            Prompt text.

        default:
            Optional default value.

        allow_empty:
            Whether an empty response is allowed.

    Returns:
        User input string.
    """
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()

        if raw == "" and default is not None:
            return default

        if raw == "" and allow_empty:
            return raw

        if raw != "":
            return raw

        print("Please enter a value.")

def prompt_yes_no(
    prompt: str,
    *,
    default: bool = True,
) -> bool:
    """
    Prompt for a yes/no answer.
    """
    suffix = "[Y/n]" if default else "[y/N]"

    while True:
        raw = input(f"{prompt} {suffix}: ").strip().lower()

        if raw == "":
            return default

        if raw in {"y", "yes"}:
            return True

        if raw in {"n", "no"}:
            return False

        print("Please enter y or n.")

def prompt_int(
    prompt: str,
    *,
    default: int | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
    allow_empty: bool = False,
) -> int | None:
    """
    Prompt for an integer.
    """
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()

        if raw == "":
            if default is not None:
                return default

            if allow_empty:
                return None

        try:
            value = int(raw)
        except ValueError:
            print("Please enter a valid integer.")
            continue

        if min_value is not None and value < min_value:
            print(f"Value must be >= {min_value}.")
            continue

        if max_value is not None and value > max_value:
            print(f"Value must be <= {max_value}.")
            continue

        return value

def prompt_choice(
    title: str,
    options: list[tuple[str, str]],
    *,
    default_key: str | None = None,
    allow_back: bool = False,
    allow_quit: bool = False,
) -> str:
    """
    Prompt the user to choose from numbered options.

    Args:
        title:
            Menu title.

        options:
            List of (key, label) pairs.

        default_key:
            Optional default key used when Enter is pressed.

        allow_back:
            Adds a "Back" option.

        allow_quit:
            Adds a "Quit" option.

    Returns:
        Selected option key.
    """
    if not options:
        raise ValueError("prompt_choice requires at least one option.")

    option_map = {key: label for key, label in options}

    if default_key is not None and default_key not in option_map:
        raise ValueError(f"default_key {default_key!r} is not present in options.")

    while True:
        print_subheader(title)

        numbered_options = list(options)

        for index, (key, label) in enumerate(numbered_options, start=1):
            marker = " *" if key == default_key else ""
            print(f"{index:>2}. {label}{marker}")

        special_start = len(numbered_options) + 1

        if allow_back:
            print(f"{special_start:>2}. Back")
            special_start += 1

        if allow_quit:
            print(f"{special_start:>2}. Quit")

        if default_key is not None:
            print(f"\nPress Enter for default: {option_map[default_key]}")

        raw = input("\nSelect an option: ").strip()

        if raw == "" and default_key is not None:
            return default_key

        try:
            selected_index = int(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue

        if 1 <= selected_index <= len(numbered_options):
            return numbered_options[selected_index - 1][0]

        current_special = len(numbered_options) + 1

        if allow_back and selected_index == current_special:
            return "__back__"

        if allow_back:
            current_special += 1

        if allow_quit and selected_index == current_special:
            return "__quit__"

        print("Selection out of range.")

def prompt_multi_choice(
    title: str,
    options: list[tuple[str, str]],
) -> list[str]:
    """
    Prompt the user to choose multiple numbered options.

    Users can enter:
        1,2,3
        all
        none
    """
    if not options:
        return []

    while True:
        print_subheader(title)

        for index, (_, label) in enumerate(options, start=1):
            print(f"{index:>2}. {label}")

        raw = input(
            "\nSelect one or more numbers separated by commas "
            "(or 'all' / 'none'): "
        ).strip().lower()

        if raw in {"", "none", "n"}:
            return []

        if raw == "all":
            return [key for key, _ in options]

        parts = [part.strip() for part in raw.split(",") if part.strip()]

        selected_keys: list[str] = []
        valid = True

        for part in parts:
            try:
                index = int(part)
            except ValueError:
                valid = False
                break

            if not 1 <= index <= len(options):
                valid = False
                break

            selected_keys.append(options[index - 1][0])

        if valid:
            seen: set[str] = set()
            unique_keys: list[str] = []

            for key in selected_keys:
                if key not in seen:
                    seen.add(key)
                    unique_keys.append(key)

            return unique_keys

        print("Invalid selection. Please try again.")

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
    formats = get_supported_formats(dataset_key)

    options: list[tuple[str, str]] = []

    for fmt in formats:
        description = FORMAT_DESCRIPTIONS.get(fmt, fmt.upper())
        options.append((fmt, description))

    return options

def object_type_options() -> list[tuple[str, str]]:
    """
    Return object-type preset options.
    """
    return [
        (
            key,
            f"{value['label']} - {value['description']}",
        )
        for key, value in OBJECT_TYPE_FILTERS.items()
    ]

def orbit_regime_options() -> list[tuple[str, str]]:
    """
    Return orbit-regime preset options.
    """
    return [
        (
            key,
            f"{value['label']} - {value['description']}",
        )
        for key, value in ORBIT_REGIME_FILTERS.items()
    ]

def rcs_size_options() -> list[tuple[str, str]]:
    """
    Return RCS-size preset options.
    """
    return [
        (
            key,
            f"{value['label']} - {value['description']}",
        )
        for key, value in RCS_SIZE_FILTERS.items()
    ]

def epoch_recency_options() -> list[tuple[str, str]]:
    """
    Return epoch-recency preset options.
    """
    return [
        (
            key,
            f"{value['label']} - {value['description']}",
        )
        for key, value in EPOCH_RECENCY_FILTERS.items()
    ]

def creation_date_recency_options() -> list[tuple[str, str]]:
    """
    Return creation-date-recency preset options.
    """
    return [
        (
            key,
            f"{value['label']} - {value['description']}",
        )
        for key, value in CREATION_DATE_RECENCY_FILTERS.items()
    ]

def country_options() -> list[tuple[str, str]]:
    """
    Return country preset options.
    """
    return [
        (
            key,
            value["label"],
        )
        for key, value in COUNTRY_PRESETS.items()
    ]

def favorite_options() -> list[tuple[str, str]]:
    """
    Return favorites preset options.
    """
    return [
        (
            key,
            value["label"],
        )
        for key, value in FAVORITES_PRESETS.items()
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

def ask_object_type_filter() -> dict[str, str]:
    """
    Ask the user for an object-type preset.
    """
    selected = prompt_choice(
        "Object type / object population",
        object_type_options(),
        default_key="all_on_orbit",
    )

    return dict(OBJECT_TYPE_FILTERS[selected]["filters"])

def ask_orbit_regime_filter() -> dict[str, str]:
    """
    Ask the user for an orbit regime filter.
    """
    selected = prompt_choice(
        "Orbit regime filter",
        orbit_regime_options(),
        default_key="all",
    )

    return dict(ORBIT_REGIME_FILTERS[selected]["filters"])

def ask_rcs_size_filter() -> dict[str, str]:
    """
    Ask the user for an RCS size filter.
    """
    selected = prompt_choice(
        "Radar cross-section size filter",
        rcs_size_options(),
        default_key="all",
    )

    return dict(RCS_SIZE_FILTERS[selected]["filters"])

def ask_epoch_recency_filter() -> dict[str, str]:
    """
    Ask the user for an EPOCH recency filter.
    """
    selected = prompt_choice(
        "EPOCH recency filter",
        epoch_recency_options(),
        default_key="all",
    )

    return dict(EPOCH_RECENCY_FILTERS[selected]["filters"])

def ask_creation_date_recency_filter() -> dict[str, str]:
    """
    Ask the user for a CREATION_DATE recency filter.
    """
    selected = prompt_choice(
        "CREATION_DATE recency filter",
        creation_date_recency_options(),
        default_key="all",
    )
    return dict(CREATION_DATE_RECENCY_FILTERS[selected]["filters"])

def ask_country_filter(predicate_name: str) -> dict[str, str]:
    """
    Ask the user for a country/owner filter.

    Args:
        predicate_name:
            Predicate to use, usually COUNTRY_CODE for GP/decay or COUNTRY for SATCAT.
    """
    selected = prompt_choice(
        "Country / owner filter",
        country_options(),
        default_key="all",
    )

    value = get_country_code(selected)

    if value is None:
        return {}

    if value == "custom":
        custom_value = prompt_text(
            "Enter Space-Track country/owner code",
            allow_empty=False,
        ).upper()
        return {predicate_name: custom_value}

    return {predicate_name: value}

def ask_favorites_filter() -> str | None:
    """
    Ask the user whether to apply a favorites filter.
    """
    use_favorites = prompt_yes_no(
        "Filter by Space-Track favorites list?",
        default=False,
    )

    if not use_favorites:
        return None

    selected = prompt_choice(
        "Favorites list",
        favorite_options(),
        default_key="geosynchronous",
    )

    return get_favorite_value(selected)

def ask_norad_filter() -> dict[str, str]:
    """
    Ask for optional NORAD_CAT_ID filter.
    """
    use_filter = prompt_yes_no(
        "Filter by NORAD catalog ID, comma list, or range?",
        default=False,
    )

    if not use_filter:
        return {}

    print(
        "\nExamples:\n"
        "  25544\n"
        "  25544,43013,48274\n"
        "  25544--26000\n"
        "  >40000\n"
        "  <100000"
    )

    value = prompt_text("NORAD_CAT_ID value")

    return {"NORAD_CAT_ID": value}

def ask_object_name_filter(predicate_name: str) -> dict[str, str]:
    """
    Ask for optional object-name or satellite-name wildcard filter.
    """
    use_filter = prompt_yes_no(
        f"Filter by {predicate_name} wildcard/name?",
        default=False,
    )

    if not use_filter:
        return {}

    print(
        "\nExamples:\n"
        "  ISS\n"
        "  STARLINK~~\n"
        "  OBJECT~~\n"
        "  COSMOS~~"
    )

    value = prompt_text(f"{predicate_name} value")

    return {predicate_name: value}

def ask_date_range_filter(
    predicate_name: str,
    *,
    default: str | None = None,
) -> dict[str, str]:
    """
    Ask for a date/date-range filter value.

    Callers ask whether to filter by the predicate first, so this only
    prompts for the value. Pressing Enter accepts default when one is given.
    """
    print(
        "\nExamples:\n"
        "  >now-7\n"
        "  2025-01-01--2025-01-31\n"
        "  >2025-01-01\n"
        "  <2025-12-31"
    )

    value = prompt_text(f"{predicate_name} value", default=default)

    return {predicate_name: value}

def ask_limit() -> int | None:
    """
    Ask for optional result limit.
    """
    use_limit = prompt_yes_no(
        "Apply a result limit?",
        default=False,
    )

    if not use_limit:
        return None

    return prompt_int(
        "Maximum number of rows/records",
        min_value=1,
        allow_empty=False,
    )

def ask_offset(limit: int | None) -> int | None:
    """
    Ask for optional result offset when limit is provided.
    """
    if limit is None:
        return None

    use_offset = prompt_yes_no(
        "Apply an offset with the limit?",
        default=False,
    )

    if not use_offset:
        return None

    return prompt_int(
        "Offset",
        min_value=0,
        allow_empty=False,
    )

def ask_orderby(dataset: DatasetConfig) -> str | None:
    """
    Ask for optional custom orderby value.
    """
    default = dataset.default_orderby

    if default:
        use_default = prompt_yes_no(
            f"Use default ordering ({default})?",
            default=True,
        )

        if use_default:
            return default

    use_orderby = prompt_yes_no(
        "Apply custom orderby?",
        default=False,
    )

    if not use_orderby:
        return None

    print(
        "\nExamples:\n"
        "  NORAD_CAT_ID\n"
        "  EPOCH desc\n"
        "  CREATED desc\n"
        "  DECAY_EPOCH desc"
    )

    return prompt_text("orderby value")

def ask_predicates(dataset_key: str) -> list[str] | None:
    """
    Ask for optional returned predicates.

    If the user chooses no selection, Space-Track returns the default/all fields.
    """
    use_predicates = prompt_yes_no(
        "Select specific returned predicates/columns?",
        default=False,
    )

    if not use_predicates:
        return None

    common_filters = get_common_filters(dataset_key)

    if common_filters:
        options = [
            (
                predicate,
                f"{predicate} - {PREDICATE_DESCRIPTIONS.get(predicate, 'No description available')}",
            )
            for predicate in common_filters
        ]

        selected = prompt_multi_choice(
            "Select returned predicates/columns",
            options,
        )

        if selected:
            return selected

    print(
        "\nEnter comma-separated predicate names.\n"
        "Example: NORAD_CAT_ID,OBJECT_NAME,EPOCH"
    )

    raw = prompt_text("Predicates")

    predicates = [
        item.strip()
        for item in raw.split(",")
        if item.strip()
    ]

    return predicates or None

def ask_custom_filters() -> dict[str, str]:
    """
    Ask for advanced custom predicate/value filters.
    """
    filters: dict[str, str] = {}

    use_custom = prompt_yes_no(
        "Add advanced custom predicate/value filters?",
        default=False,
    )

    if not use_custom:
        return filters

    print(
        "\nAdd custom Space-Track REST filters one at a time.\n"
        "Examples:\n"
        "  Predicate: NORAD_CAT_ID      Value: 25544,43013\n"
        "  Predicate: EPOCH             Value: >now-30\n"
        "  Predicate: OBJECT_NAME       Value: STARLINK~~\n"
        "  Predicate: PERIOD            Value: 1430--1450\n"
        "  Predicate: DECAY_DATE        Value: null-val\n"
    )

    while True:
        predicate = prompt_text(
            "Predicate name",
            allow_empty=False,
        ).upper()

        value = prompt_text(
            f"Value for {predicate}",
            allow_empty=False,
        )

        filters[predicate] = value

        another = prompt_yes_no(
            "Add another custom filter?",
            default=False,
        )

        if not another:
            break

    return filters

# =============================================================================
# Dataset-specific configuration flows
# =============================================================================

def configure_gp_like_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure GP or GP_HISTORY dataset options.
    """
    filters: dict[str, str] = {}

    print_header(dataset.label)
    print(dataset.description)

    if dataset.key == "gp":
        filters = merge_filters(filters, ask_object_type_filter())

    else:
        print_warning(
            "Historical GP queries can be very large. Use NORAD_CAT_ID and a "
            "short EPOCH or CREATION_DATE range whenever possible."
        )
        filters = merge_filters(filters, ask_norad_filter())

    if prompt_yes_no("Configure orbit-regime filter?", default=True):
        filters = merge_filters(filters, ask_orbit_regime_filter())

    if prompt_yes_no("Configure RCS-size filter?", default=False):
        filters = merge_filters(filters, ask_rcs_size_filter())

    if prompt_yes_no("Configure EPOCH recency filter?", default=True):
        filters = merge_filters(filters, ask_epoch_recency_filter())

    if prompt_yes_no("Configure CREATION_DATE recency filter?", default=False):
        filters = merge_filters(filters, ask_creation_date_recency_filter())

    filters = merge_filters(filters, ask_country_filter("COUNTRY_CODE"))

    # gp_history already asked for NORAD_CAT_ID after its size warning.
    if dataset.key == "gp":
        filters = merge_filters(filters, ask_norad_filter())

    filters = merge_filters(filters, ask_object_name_filter("OBJECT_NAME"))

    if prompt_yes_no("Filter by launch site SITE?", default=False):
        site = prompt_text("SITE value, for example AFETR, TTMTR, FRGUI").upper()
        filters["SITE"] = site

    if prompt_yes_no("Filter by LAUNCH_DATE?", default=False):
        filters = merge_filters(filters, ask_date_range_filter("LAUNCH_DATE"))

    custom_filters = ask_custom_filters()
    filters = merge_filters(filters, custom_filters)

    favorites = ask_favorites_filter()

    return {
        "filters": remove_empty_filters(filters),
        "favorites": favorites,
    }

def configure_satcat_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure SATCAT-related dataset options.
    """
    filters: dict[str, str] = {}

    print_header(dataset.label)
    print(dataset.description)

    if dataset.key == "satcat":
        current_only = prompt_yes_no(
            "Use only current SATCAT records?",
            default=True,
        )

        if current_only:
            filters["CURRENT"] = "Y"

        if prompt_yes_no("Filter by on-orbit only using DECAY/null-val?", default=False):
            filters["DECAY"] = "null-val"

        if prompt_yes_no("Filter by object type?", default=False):
            object_type = prompt_choice(
                "SATCAT object type",
                [
                    ("PAYLOAD", "PAYLOAD"),
                    ("ROCKET BODY", "ROCKET BODY"),
                    ("DEBRIS", "DEBRIS"),
                    ("UNKNOWN", "UNKNOWN"),
                ],
                default_key="PAYLOAD",
            )
            filters["OBJECT_TYPE"] = object_type

        filters = merge_filters(filters, ask_country_filter("COUNTRY"))

        if prompt_yes_no("Filter by launch date LAUNCH?", default=False):
            filters = merge_filters(filters, ask_date_range_filter("LAUNCH"))

        if prompt_yes_no("Filter by decay date DECAY?", default=False):
            filters = merge_filters(filters, ask_date_range_filter("DECAY"))

        if prompt_yes_no("Filter by launch site SITE?", default=False):
            site = prompt_text("SITE value").upper()
            filters["SITE"] = site

        filters = merge_filters(filters, ask_norad_filter())
        filters = merge_filters(filters, ask_object_name_filter("SATNAME"))

    elif dataset.key == "satcat_debut":
        if prompt_yes_no("Use recent DEBUT filter?", default=True):
            filters["DEBUT"] = prompt_text(
                "DEBUT value",
                default=">now-1",
            )

        filters = merge_filters(filters, ask_norad_filter())
        filters = merge_filters(filters, ask_object_name_filter("SATNAME"))
        filters = merge_filters(filters, ask_country_filter("COUNTRY"))

    elif dataset.key == "satcat_change":
        if prompt_yes_no("Filter by CHANGE_DATE?", default=True):
            filters = merge_filters(
                filters,
                ask_date_range_filter(
                    "CHANGE_DATE",
                    default=dataset.recommended_filters.get("CHANGE_DATE", ">now-7"),
                ),
            )

        filters = merge_filters(filters, ask_norad_filter())
        filters = merge_filters(filters, ask_object_name_filter("SATNAME"))
        filters = merge_filters(filters, ask_country_filter("COUNTRY"))

    elif dataset.key == "launch_site":
        if prompt_yes_no("Filter by SITE_CODE?", default=False):
            filters["SITE_CODE"] = prompt_text("SITE_CODE").upper()

        if prompt_yes_no("Filter by LAUNCH_SITE wildcard/name?", default=False):
            filters["LAUNCH_SITE"] = prompt_text(
                "LAUNCH_SITE value, for example CAPE~~"
            )

    custom_filters = ask_custom_filters()
    filters = merge_filters(filters, custom_filters)

    return {
        "filters": remove_empty_filters(filters),
        "favorites": None,
    }

def configure_decay_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure decay or TIP dataset options.
    """
    filters: dict[str, str] = {}

    print_header(dataset.label)
    print(dataset.description)

    filters = merge_filters(filters, ask_norad_filter())

    if dataset.key == "decay":
        if prompt_yes_no("Filter by MSG_EPOCH?", default=False):
            filters = merge_filters(filters, ask_date_range_filter("MSG_EPOCH"))

        if prompt_yes_no("Filter by DECAY_EPOCH?", default=True):
            filters = merge_filters(
                filters,
                ask_date_range_filter(
                    "DECAY_EPOCH",
                    default=dataset.recommended_filters.get("DECAY_EPOCH", ">now-7"),
                ),
            )

        if prompt_yes_no("Filter by object name?", default=False):
            filters = merge_filters(filters, ask_object_name_filter("OBJECT_NAME"))

        filters = merge_filters(filters, ask_country_filter("COUNTRY_CODE"))

        if prompt_yes_no("Filter by RCS_SIZE?", default=False):
            filters = merge_filters(filters, ask_rcs_size_filter())

        if prompt_yes_no("Filter by PRECEDENCE?", default=False):
            print(
                "\nPRECEDENCE examples:\n"
                "  4 = 60-day decay message\n"
                "  3 = TIP message\n"
                "  2 = Decay message\n"
                "  1 = SATCAT most recent decay date"
            )
            filters["PRECEDENCE"] = prompt_text("PRECEDENCE value")

    elif dataset.key == "tip":
        if prompt_yes_no("Filter by INSERT_EPOCH?", default=True):
            filters = merge_filters(
                filters,
                ask_date_range_filter(
                    "INSERT_EPOCH",
                    default=dataset.recommended_filters.get("INSERT_EPOCH", ">now-7"),
                ),
            )

        if prompt_yes_no("Filter by MSG_EPOCH?", default=False):
            filters = merge_filters(filters, ask_date_range_filter("MSG_EPOCH"))

        if prompt_yes_no("Filter by DECAY_EPOCH?", default=False):
            filters = merge_filters(filters, ask_date_range_filter("DECAY_EPOCH"))

        if prompt_yes_no("Filter high-interest TIPs only?", default=False):
            filters["HIGH_INTEREST"] = "Y"

    custom_filters = ask_custom_filters()
    filters = merge_filters(filters, custom_filters)

    return {
        "filters": remove_empty_filters(filters),
        "favorites": None,
    }

def configure_cdm_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure public CDM dataset options.
    """
    filters: dict[str, str] = {}

    print_header(dataset.label)
    print(dataset.description)

    if prompt_yes_no("Filter by CREATED date?", default=True):
        filters = merge_filters(
            filters,
            ask_date_range_filter(
                "CREATED",
                default=dataset.recommended_filters.get("CREATED", ">now-7"),
            ),
        )

    if prompt_yes_no("Filter by TCA date?", default=False):
        filters = merge_filters(filters, ask_date_range_filter("TCA"))

    if prompt_yes_no("Filter by SAT_1_ID?", default=False):
        filters["SAT_1_ID"] = prompt_text("SAT_1_ID value")

    if prompt_yes_no("Filter by SAT_2_ID?", default=False):
        filters["SAT_2_ID"] = prompt_text("SAT_2_ID value")

    if prompt_yes_no("Emergency-reportable only?", default=False):
        filters["EMERGENCY_REPORTABLE"] = "Y"

    if prompt_yes_no("Filter by minimum collision probability PC?", default=False):
        filters["PC"] = prompt_text("PC value, for example >0.00001")

    if prompt_yes_no("Filter by maximum MIN_RNG?", default=False):
        filters["MIN_RNG"] = prompt_text("MIN_RNG value, for example <5")

    custom_filters = ask_custom_filters()
    filters = merge_filters(filters, custom_filters)

    return {
        "filters": remove_empty_filters(filters),
        "favorites": None,
    }

def configure_boxscore_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure boxscore dataset options.
    """
    filters: dict[str, str] = {}

    print_header(dataset.label)
    print(dataset.description)

    if prompt_yes_no("Filter by country?", default=False):
        filters = merge_filters(filters, ask_country_filter("COUNTRY"))

    custom_filters = ask_custom_filters()
    filters = merge_filters(filters, custom_filters)

    return {
        "filters": remove_empty_filters(filters),
        "favorites": None,
    }

def configure_publicfiles_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure publicfiles endpoint options.
    """
    filters: dict[str, str] = {}
    publicfiles_download_name: str | None = None

    print_header(dataset.label)
    print(dataset.description)

    if dataset.key == "publicfiles_download":
        print(
            "\nTo download a public file, first use:\n"
            "  Public files - detailed file metadata\n"
            "Then copy the LINK value into this prompt."
        )
        publicfiles_download_name = prompt_text("Public file LINK/name value")
        filters["name"] = publicfiles_download_name

    return {
        "filters": remove_empty_filters(filters),
        "favorites": None,
        "publicfiles_download_name": publicfiles_download_name,
    }

def configure_generic_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Generic configuration fallback for datasets without a custom flow.
    """
    filters: dict[str, str] = {}

    print_header(dataset.label)
    print(dataset.description)

    custom_filters = ask_custom_filters()
    filters = merge_filters(filters, custom_filters)

    return {
        "filters": remove_empty_filters(filters),
        "favorites": None,
    }

def configure_dataset_filters(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Route to the correct dataset-specific configuration flow.
    """
    if dataset.key in {"gp", "gp_history"}:
        return configure_gp_like_dataset(dataset)

    if dataset.key in {"satcat", "satcat_change", "satcat_debut", "launch_site"}:
        return configure_satcat_dataset(dataset)

    if dataset.key in {"decay", "tip"}:
        return configure_decay_dataset(dataset)

    if dataset.key == "cdm_public":
        return configure_cdm_dataset(dataset)

    if dataset.key == "boxscore":
        return configure_boxscore_dataset(dataset)

    if dataset_uses_publicfiles_controller(dataset.key):
        return configure_publicfiles_dataset(dataset)

    return configure_generic_dataset(dataset)

# =============================================================================
# Output/query configuration
# =============================================================================

def choose_output_format(dataset_key: str) -> str:
    """
    Ask the user to choose an output format.
    """
    default_format = get_default_format(dataset_key)

    selected = prompt_choice(
        "Output format",
        format_options_for_dataset(dataset_key),
        default_key=default_format,
    )

    validate_dataset_format(dataset_key, selected)

    if should_warn_legacy_tle(dataset_key, selected):
        print_warning(
            "TLE/3LE are legacy fixed-width formats. JSON, CSV, XML, or KVN "
            "are usually better for expanded catalog identifiers."
        )

    return selected

def configure_query_options(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure output format, predicates, ordering, limit, metadata, and other
    query-level options.
    """
    output_format = choose_output_format(dataset.key)

    predicates = None

    if output_format not in {"tle", "3le", "raw"}:
        predicates = ask_predicates(dataset.key)

    orderby = None
    limit = None
    offset = None
    metadata = False
    show_empty = False
    distinct = False

    if not dataset_uses_publicfiles_controller(dataset.key):
        orderby = ask_orderby(dataset)
        limit = ask_limit()
        offset = ask_offset(limit)

        if output_format not in {"csv", "tle", "3le", "kvn"}:
            metadata = prompt_yes_no(
                "Request Space-Track metadata?",
                default=False,
            )

        show_empty = prompt_yes_no(
            "Show explicit message for empty result?",
            default=True,
        )

        distinct = prompt_yes_no(
            "Request distinct rows only?",
            default=False,
        )

    return {
        "output_format": output_format,
        "predicates": predicates,
        "orderby": orderby,
        "limit": limit,
        "offset": offset,
        "metadata": metadata,
        "show_empty": show_empty,
        "distinct": distinct,
    }

def configure_export_options(dataset_key: str, output_format: str) -> dict[str, Any]:
    """
    Configure output filename/directory options.
    """
    print_subheader("Export options")

    download_dir_raw = prompt_text(
        "Download directory",
        default=str(DEFAULT_DOWNLOAD_DIR),
    )
    download_dir = Path(download_dir_raw)

    use_custom_name = prompt_yes_no(
        "Use custom output filename base?",
        default=False,
    )

    custom_name = None

    if use_custom_name:
        custom_name = prompt_text(
            "Custom filename base without extension",
            allow_empty=False,
        )

    overwrite = prompt_yes_no(
        "Overwrite existing file if same name exists?",
        default=False,
    )

    pretty_json = True

    if output_format == "json":
        pretty_json = prompt_yes_no(
            "Pretty-print JSON output?",
            default=True,
        )

    return {
        "download_dir": download_dir,
        "custom_name": custom_name,
        "overwrite": overwrite,
        "pretty_json": pretty_json,
    }

# =============================================================================
# Advanced custom query mode
# =============================================================================

def choose_dataset_directly() -> DatasetConfig:
    """
    Let the user choose any dataset directly.
    """
    options = [
        (
            key,
            f"{dataset.label} - class/{dataset.api_class}",
        )
        for key, dataset in DATASETS.items()
    ]

    selected = prompt_choice(
        "Choose Space-Track dataset/class",
        options,
    )

    return get_dataset(selected)

def run_advanced_custom_query(client: SpaceTrackClient) -> None:
    """
    Run the advanced custom query builder.
    """
    print_header("Advanced Custom Query Builder")

    dataset = choose_dataset_directly()

    filters: dict[str, str] = {}

    print(
        "\nYou can now add any Space-Track predicate/value filters supported "
        "by the selected class."
    )

    filters = ask_custom_filters()

    if not filters:
        print_warning("No custom filters were added.")

    query_options = configure_query_options(dataset)

    publicfiles_download_name = None

    if dataset.key == "publicfiles_download":
        publicfiles_download_name = prompt_text("Public file LINK/name value")
        filters["name"] = publicfiles_download_name

    execute_download_flow(
        client=client,
        dataset=dataset,
        filters=filters,
        favorites=None,
        publicfiles_download_name=publicfiles_download_name,
        query_options=query_options,
    )

# =============================================================================
# Query execution
# =============================================================================

def execute_download_flow(
    *,
    client: SpaceTrackClient,
    dataset: DatasetConfig,
    filters: dict[str, str],
    favorites: str | None,
    publicfiles_download_name: str | None,
    query_options: dict[str, Any],
) -> None:
    """
    Build, preview, execute, export, and save metadata for a query.
    """
    output_format = query_options["output_format"]

    try:
        url = build_query_url(
            dataset_key=dataset.key,
            filters=filters,
            output_format=output_format,
            predicates=query_options.get("predicates"),
            orderby=query_options.get("orderby"),
            limit=query_options.get("limit"),
            offset=query_options.get("offset"),
            metadata=query_options.get("metadata", False),
            show_empty=query_options.get("show_empty", False),
            favorites=favorites,
            distinct=query_options.get("distinct", False),
            publicfiles_download_name=publicfiles_download_name,
            use_recommended_filters=False,
        )

        query_summary = summarize_query(
            dataset_key=dataset.key,
            filters=filters,
            output_format=output_format,
            predicates=query_options.get("predicates"),
            orderby=query_options.get("orderby"),
            limit=query_options.get("limit"),
            offset=query_options.get("offset"),
            metadata=query_options.get("metadata", False),
            show_empty=query_options.get("show_empty", False),
            favorites=favorites,
            distinct=query_options.get("distinct", False),
            publicfiles_download_name=publicfiles_download_name,
            use_recommended_filters=False,
        )

    except QueryBuilderError as exc:
        print_warning(f"Could not build query: {exc}")
        return

    print_query_summary(query_summary)

    if not prompt_yes_no("Proceed with download?", default=True):
        print_info("Download cancelled.")
        return

    export_options = configure_export_options(
        dataset_key=dataset.key,
        output_format=output_format,
    )

    try:
        print_info("Sending request to Space-Track...")

        response = client.get(
            url,
            timeout_seconds=client.download_timeout_seconds,
        )

        print_success(
            f"Request completed with HTTP {response.status_code} "
            f"in {response.elapsed_seconds:.2f} seconds."
        )

    except SpaceTrackAuthenticationError as exc:
        print_warning(f"Authentication error: {exc}")
        return

    except SpaceTrackRequestError as exc:
        print_warning(f"Request failed: {exc}")
        return

    except SpaceTrackClientError as exc:
        print_warning(f"Space-Track client error: {exc}")
        return

    try:
        # Checked before the generic raw branch: publicfiles_download is
        # always raw, and should keep its original file name.
        if dataset.key == "publicfiles_download":
            original_name = (
                export_options["custom_name"]
                or publicfiles_download_name
                or "space_track_public_file"
            )

            export_result = export_public_file_bytes(
                content=response.content,
                original_name=original_name,
                download_dir=export_options["download_dir"],
                overwrite=export_options["overwrite"],
                print_preview=True,
            )

        elif output_format == "raw":
            export_result = export_binary_response(
                content=response.content,
                dataset_key=dataset.key,
                output_format="raw",
                download_dir=export_options["download_dir"],
                custom_name=export_options["custom_name"],
                overwrite=export_options["overwrite"],
                print_preview=True,
            )

        else:
            export_result = export_response(
                content=response.text,
                dataset_key=dataset.key,
                output_format=output_format,
                download_dir=export_options["download_dir"],
                custom_name=export_options["custom_name"],
                overwrite=export_options["overwrite"],
                pretty_json=export_options["pretty_json"],
                print_preview=True,
            )

    except Exception as exc:
        print_warning(f"Failed to export response: {exc}")
        return

    try:
        save_metadata_for_export(
            query_summary=query_summary,
            export_result=export_result,
            response_status_code=response.status_code,
            response_elapsed_seconds=response.elapsed_seconds,
            response_headers=response.headers,
            overwrite=export_options["overwrite"],
            print_summary=True,
        )

    except Exception as exc:
        print_warning(f"Downloaded data was saved, but metadata saving failed: {exc}")

    print_success("Done.")

def run_dataset_flow(client: SpaceTrackClient, dataset_key: str) -> None:
    """
    Run the full configuration/download flow for one dataset.
    """
    dataset = get_dataset(dataset_key)

    filter_config = configure_dataset_filters(dataset)
    query_options = configure_query_options(dataset)

    execute_download_flow(
        client=client,
        dataset=dataset,
        filters=filter_config.get("filters", {}),
        favorites=filter_config.get("favorites"),
        publicfiles_download_name=filter_config.get("publicfiles_download_name"),
        query_options=query_options,
    )


# =============================================================================
# Main menu loop
# =============================================================================

def run_main_menu(client: SpaceTrackClient) -> None:
    """
    Run the main interactive menu loop.
    """
    while True:
        selected_group = prompt_choice(
            "Main menu",
            dataset_group_options(),
            allow_quit=True,
        )

        if selected_group == "__quit__":
            print_info("Exiting.")
            return

        if selected_group == "session_status":
            client.print_session_status()
            prompt_enter_to_continue()
            continue

        if selected_group == "advanced_custom":
            run_advanced_custom_query(client)
            prompt_enter_to_continue()
            continue

        dataset_options = dataset_options_for_group(selected_group)

        selected_dataset = prompt_choice(
            "Choose dataset",
            dataset_options,
            allow_back=True,
            allow_quit=True,
        )

        if selected_dataset == "__back__":
            continue

        if selected_dataset == "__quit__":
            print_info("Exiting.")
            return

        run_dataset_flow(client, selected_dataset)
        prompt_enter_to_continue()

# =============================================================================
# Startup checks
# =============================================================================

def print_rate_limit_reminder() -> None:
    """
    Print a reminder about responsible API use.
    """
    print_subheader("Responsible API use reminder")
    print(
        "Space-Track throttles API usage to preserve service quality.\n"
        "Avoid repeated large downloads and avoid hundreds of small per-object queries.\n"
        "Prefer efficient combined filters, date windows, and saved local copies."
    )


def confirm_start() -> bool:
    """
    Confirm that the user wants to start.
    """
    print_rate_limit_reminder()

    return prompt_yes_no(
        "Continue?",
        default=True,
    )

# =============================================================================
# Main entry point
# =============================================================================

def main() -> int:
    """
    Main program entry point.

    Returns:
        Process exit code.
    """
    print_app_banner()

    if not confirm_start():
        print_info("Cancelled.")
        return 0

    client: SpaceTrackClient | None = None

    try:
        client = create_logged_in_client(
            allow_prompt=True,
        )

        run_main_menu(client)

        return 0

    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user.")
        return 130

    except SpaceTrackAuthenticationError as exc:
        print_warning(f"Authentication failed: {exc}")
        return 1

    except SpaceTrackClientError as exc:
        print_warning(f"Space-Track client error: {exc}")
        return 1

    except Exception as exc:
        print_warning(f"Unexpected error: {exc}")
        return 1

    finally:
        if client is not None:
            try:
                if client.logged_in:
                    client.logout()
            finally:
                client.close()


if __name__ == "__main__":
    sys.exit(main())