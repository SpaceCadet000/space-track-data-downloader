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
    DATASETS,
    DatasetConfig,
    get_country_code,
    get_dataset,
    get_default_format,
    validate_dataset_format,
)
from downloader_core import (
    CUSTOM_FIELD,
    DATE_HELP,
    FAVORITES_FIELD,
    ORDERBY_HELP,
    CUSTOM_FILTER_HELP,
    FilterField,
    build_filter_config,
    country_field,
    country_options,
    creation_date_recency_options,
    dataset_filter_fields,
    dataset_flow,
    dataset_group_options,
    dataset_options_for_group,
    dataset_warning,
    epoch_recency_options,
    export_download,
    favorite_options,
    fetch,
    format_options_for_dataset,
    format_warning,
    merge_filters,
    name_field,
    norad_field,
    object_type_options,
    orbit_regime_options,
    predicate_options,
    prepare_query,
    query_option_availability,
    rcs_size_options,
    remove_empty_filters,
    resolve_favorites,
    resolve_field,
    save_download_metadata,
)
from exporters import DEFAULT_DOWNLOAD_DIR
from query_builder import (
    QueryBuilderError,
    print_query_summary,
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
# Filter prompts
# =============================================================================
#
# The questions themselves are declared in downloader_core.dataset_filter_fields;
# these helpers only ask them. Option builders, merge_filters and
# remove_empty_filters are re-exported from downloader_core above.

def ask_custom_filter_entries() -> dict[str, str]:
    """
    Ask for custom predicate/value pairs until the user stops.
    """
    print(f"\n{CUSTOM_FILTER_HELP}")

    filters: dict[str, str] = {}

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

def ask_field(spec: FilterField) -> Any:
    """
    Ask one filter question.

    Returns:
        The field value for build_filter_config, or None when the gate
        question was answered "no".
    """
    if spec.gate is not None and not prompt_yes_no(spec.gate, default=spec.gate_default):
        return None

    if spec.kind == "flag":
        return True

    if spec.kind == "custom":
        return ask_custom_filter_entries()

    if spec.kind in {"preset", "choice", "favorites"}:
        return prompt_choice(spec.label, spec.choices(), default_key=spec.default)

    if spec.kind == "country":
        selected = prompt_choice(spec.label, spec.choices(), default_key=spec.default)

        if get_country_code(selected) == "custom":
            custom_value = prompt_text(
                "Enter Space-Track country/owner code",
                allow_empty=False,
            )
            return {"preset": selected, "custom": custom_value}

        return selected

    if spec.help:
        print(f"\n{spec.help}")

    return prompt_text(spec.label, default=spec.default)

def ask_preset_filter(table_name: str, title: str) -> dict[str, str]:
    """
    Ask for one preset-table option and return its filters.
    """
    spec = FilterField(table_name, "preset", title, default="all", preset_table=table_name)
    return resolve_field(spec, ask_field(spec))

def ask_object_type_filter() -> dict[str, str]:
    """
    Ask the user for an object-type preset.
    """
    spec = FilterField(
        "object_type", "preset", "Object type / object population",
        default="all_on_orbit", preset_table="object_type",
    )
    return resolve_field(spec, ask_field(spec))

def ask_orbit_regime_filter() -> dict[str, str]:
    """
    Ask the user for an orbit regime filter.
    """
    return ask_preset_filter("orbit_regime", "Orbit regime filter")

def ask_rcs_size_filter() -> dict[str, str]:
    """
    Ask the user for an RCS size filter.
    """
    return ask_preset_filter("rcs_size", "Radar cross-section size filter")

def ask_epoch_recency_filter() -> dict[str, str]:
    """
    Ask the user for an EPOCH recency filter.
    """
    return ask_preset_filter("epoch_recency", "EPOCH recency filter")

def ask_creation_date_recency_filter() -> dict[str, str]:
    """
    Ask the user for a CREATION_DATE recency filter.
    """
    return ask_preset_filter("creation_date_recency", "CREATION_DATE recency filter")

def ask_country_filter(predicate_name: str) -> dict[str, str]:
    """
    Ask the user for a country/owner filter.

    Args:
        predicate_name:
            Predicate to use, usually COUNTRY_CODE for GP/decay or COUNTRY for SATCAT.
    """
    spec = country_field(predicate_name)
    return resolve_field(spec, ask_field(spec))

def ask_favorites_filter() -> str | None:
    """
    Ask the user whether to apply a favorites filter.
    """
    selected = ask_field(FAVORITES_FIELD)
    return None if selected is None else resolve_favorites(selected)

def ask_norad_filter() -> dict[str, str]:
    """
    Ask for optional NORAD_CAT_ID filter.
    """
    spec = norad_field()
    value = ask_field(spec)
    return {} if value is None else resolve_field(spec, value)

def ask_object_name_filter(predicate_name: str) -> dict[str, str]:
    """
    Ask for optional object-name or satellite-name wildcard filter.
    """
    spec = name_field(predicate_name)
    value = ask_field(spec)
    return {} if value is None else resolve_field(spec, value)

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
    print(f"\n{DATE_HELP}")

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

    print(f"\n{ORDERBY_HELP}")

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

    options = predicate_options(dataset_key)

    if options:
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
    filters = ask_field(CUSTOM_FIELD)
    return {} if filters is None else filters

# =============================================================================
# Dataset-specific configuration flows
# =============================================================================

def run_filter_wizard(
    dataset: DatasetConfig,
    fields: list[FilterField] | None = None,
) -> dict[str, Any]:
    """
    Ask a dataset's filter questions in order and build its filter config.
    """
    print_header(dataset.label)
    print(dataset.description)

    warning = dataset_warning(dataset.key)

    if warning:
        print_warning(warning)

    specs = dataset_filter_fields(dataset.key) if fields is None else fields
    values: dict[str, Any] = {}

    for spec in specs:
        value = ask_field(spec)

        if value is not None:
            values[spec.id] = value

    return build_filter_config(dataset.key, values, fields=specs)

def configure_gp_like_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure GP or GP_HISTORY dataset options.
    """
    return run_filter_wizard(dataset)

def configure_satcat_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure SATCAT-related dataset options.
    """
    return run_filter_wizard(dataset)

def configure_decay_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure decay or TIP dataset options.
    """
    return run_filter_wizard(dataset)

def configure_cdm_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure public CDM dataset options.
    """
    return run_filter_wizard(dataset)

def configure_boxscore_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure boxscore dataset options.
    """
    return run_filter_wizard(dataset)

def configure_publicfiles_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure publicfiles endpoint options.
    """
    return run_filter_wizard(dataset)

def configure_generic_dataset(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Generic configuration fallback for datasets without a custom flow.
    """
    return run_filter_wizard(dataset, fields=[CUSTOM_FIELD])

def configure_dataset_filters(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Route to the correct dataset-specific configuration flow.
    """
    flows = {
        "gp_like": configure_gp_like_dataset,
        "satcat": configure_satcat_dataset,
        "decay": configure_decay_dataset,
        "cdm": configure_cdm_dataset,
        "boxscore": configure_boxscore_dataset,
        "publicfiles": configure_publicfiles_dataset,
    }

    return flows.get(dataset_flow(dataset.key), configure_generic_dataset)(dataset)

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

    warning = format_warning(dataset_key, selected)

    if warning:
        print_warning(warning)

    return selected

def configure_query_options(dataset: DatasetConfig) -> dict[str, Any]:
    """
    Configure output format, predicates, ordering, limit, metadata, and other
    query-level options.
    """
    output_format = choose_output_format(dataset.key)
    available = query_option_availability(dataset.key, output_format)

    predicates = None

    if available["predicates"]:
        predicates = ask_predicates(dataset.key)

    orderby = None
    limit = None
    offset = None
    metadata = False
    show_empty = False
    distinct = False

    if available["orderby"]:
        orderby = ask_orderby(dataset)

    if available["limit"]:
        limit = ask_limit()
        offset = ask_offset(limit)

    if available["metadata"]:
        metadata = prompt_yes_no(
            "Request Space-Track metadata?",
            default=False,
        )

    if available["show_empty"]:
        show_empty = prompt_yes_no(
            "Show explicit message for empty result?",
            default=True,
        )

    if available["distinct"]:
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
        prepared = prepare_query(
            dataset_key=dataset.key,
            filters=filters,
            favorites=favorites,
            publicfiles_download_name=publicfiles_download_name,
            query_options=query_options,
        )

    except QueryBuilderError as exc:
        print_warning(f"Could not build query: {exc}")
        return

    print_query_summary(prepared.summary)

    if not prompt_yes_no("Proceed with download?", default=True):
        print_info("Download cancelled.")
        return

    export_options = configure_export_options(
        dataset_key=dataset.key,
        output_format=output_format,
    )

    try:
        print_info("Sending request to Space-Track...")

        response = fetch(client, prepared.url)

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
        export_result = export_download(
            response=response,
            dataset_key=dataset.key,
            output_format=output_format,
            publicfiles_download_name=publicfiles_download_name,
            export_options=export_options,
            print_preview=True,
        )

    except Exception as exc:
        print_warning(f"Failed to export response: {exc}")
        return

    try:
        save_download_metadata(
            prepared=prepared,
            export_result=export_result,
            response=response,
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