"""
query_builder.py

Utilities for building Space-Track.org REST API query URLs safely.

This module does not perform network requests. It only builds URLs and query
paths that can be passed to spacetrack_client.py.

The main function is build_query_url(), which creates URLs like:

https://www.space-track.org/basicspacedata/query/class/gp/DECAY_DATE/null-val/EPOCH/%3Enow-10/format/json

It also supports publicfiles endpoints like:

https://www.space-track.org/publicfiles/query/class/loadpublicdata

and download URLs like:

https://www.space-track.org/publicfiles/query/class/download?name=FILENAME
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlencode

from dataset_configs import (
    BASIC_SPACE_DATA_CONTROLLER,
    PUBLIC_FILES_CONTROLLER,
    DATASETS,
    DatasetConfig,
    dataset_supports_metadata,
    dataset_uses_publicfiles_controller,
    get_dataset,
    get_default_orderby,
    get_recommended_filters,
    validate_dataset_format,
)


BASE_URL = "https://www.space-track.org"
QUERY_ACTION = "query"
MODELDEF_ACTION = "modeldef"


# =============================================================================
# Exceptions
# =============================================================================

class QueryBuilderError(Exception):
    """
    Base exception for query-builder errors.
    """


class InvalidDatasetError(QueryBuilderError):
    """
    Raised when a dataset key is invalid.
    """


class InvalidFormatError(QueryBuilderError):
    """
    Raised when an output format is invalid for a dataset.
    """


class InvalidFilterError(QueryBuilderError):
    """
    Raised when a filter is invalid.
    """


# =============================================================================
# Data containers
# =============================================================================

@dataclass
class SpaceTrackQuery:
    """
    Represents a Space-Track query before it is converted into a URL.

    Attributes:
        dataset_key:
            Key from DATASETS in dataset_configs.py.

        filters:
            Dictionary of Space-Track predicate/value filters.
            Example:
                {
                    "OBJECT_TYPE": "DEBRIS",
                    "DECAY_DATE": "null-val",
                    "EPOCH": ">now-10"
                }

        output_format:
            Space-Track output format such as json, csv, xml, kvn, html, tle,
            or 3le.

        predicates:
            Optional list of predicates/columns to return.
            Example:
                ["NORAD_CAT_ID", "OBJECT_NAME", "EPOCH"]

        orderby:
            Optional Space-Track orderby value.
            Example:
                "NORAD_CAT_ID"
                "EPOCH desc"

        limit:
            Optional number of rows to return.

        offset:
            Optional row offset to use with limit.
            If limit=10 and offset=5, Space-Track receives /limit/10,5/.

        metadata:
            Whether to request Space-Track metadata.
            This is ignored by Space-Track for csv, tle, and 3le.

        show_empty:
            Whether to include /emptyresult/show.

        favorites:
            Optional favorites list name.
            Example:
                "Geosynchronous"

        distinct:
            Whether to include /distinct/true.

        raw_extra_path:
            Optional raw REST path appended before format.
            This should be used sparingly.

        publicfiles_download_name:
            For publicfiles download endpoint only. This becomes the name query
            parameter.
    """

    dataset_key: str
    filters: dict[str, str] = field(default_factory=dict)
    output_format: str | None = None
    predicates: list[str] | tuple[str, ...] | None = None
    orderby: str | None = None
    limit: int | None = None
    offset: int | None = None
    metadata: bool = False
    show_empty: bool = False
    favorites: str | None = None
    distinct: bool = False
    raw_extra_path: str | None = None
    publicfiles_download_name: str | None = None


# =============================================================================
# URL encoding helpers
# =============================================================================

def encode_path_value(value: Any) -> str:
    """
    Encode a Space-Track REST path value safely.

    Space-Track values often use characters that have special meanings:
        >       greater than
        <       less than
        <>      not equal
        ,       OR list
        --      inclusive range
        ~~      wildcard
        ^       wildcard-after
        now     current-time variable
        null-val null value

    We preserve characters that are meaningful to Space-Track operators where
    safe, and encode characters that would break the URL path, such as spaces.

    Examples:
        "DEBRIS"        -> "DEBRIS"
        "ROCKET BODY"   -> "ROCKET%20BODY"
        ">now-10"       -> "%3Enow-10"
        "<2000"         -> "%3C2000"
        "<>null-val"    -> "%3C%3Enull-val"
        "25544,43013"   -> "25544,43013"
        "25544--26000"  -> "25544--26000"
        "STARLINK~~"    -> "STARLINK~~"
    """
    if value is None:
        raise InvalidFilterError("Filter value cannot be None.")

    text = str(value).strip()

    if text == "":
        raise InvalidFilterError("Filter value cannot be empty.")

    return quote(text, safe=",-.~")


def encode_predicate_name(predicate: str) -> str:
    """
    Encode a Space-Track predicate name.

    Predicate names are usually uppercase identifiers such as NORAD_CAT_ID.
    Spaces are not expected, but we still encode safely.
    """
    text = str(predicate).strip()

    if text == "":
        raise InvalidFilterError("Predicate name cannot be empty.")

    return quote(text, safe="_")


def encode_orderby_value(orderby: str) -> str:
    """
    Encode an orderby value.

    Space-Track orderby values may include spaces, for example:
        EPOCH desc
        NORAD_CAT_ID asc
        DECAY_EPOCH desc

    Spaces must be URL-encoded.
    """
    text = str(orderby).strip()

    if text == "":
        raise QueryBuilderError("orderby value cannot be empty.")

    return quote(text, safe=",_")


def encode_predicates(predicates: list[str] | tuple[str, ...]) -> str:
    """
    Encode a predicates list as a comma-separated Space-Track value.

    Example:
        ["NORAD_CAT_ID", "OBJECT_NAME", "EPOCH"]
        -> "NORAD_CAT_ID,OBJECT_NAME,EPOCH"
    """
    if not predicates:
        raise QueryBuilderError("Predicates list cannot be empty.")

    encoded = []

    for predicate in predicates:
        encoded.append(encode_predicate_name(predicate))

    return ",".join(encoded)


def normalize_filter_value(value: Any) -> str:
    """
    Convert a filter value to a stripped string.

    This function does not URL-encode. It is used for validation and metadata.
    """
    if value is None:
        raise InvalidFilterError("Filter value cannot be None.")

    text = str(value).strip()

    if text == "":
        raise InvalidFilterError("Filter value cannot be empty.")

    return text


def normalize_filters(filters: dict[str, Any] | None) -> dict[str, str]:
    """
    Normalize a filter dictionary.

    Empty dictionaries and None become {}.
    Predicate names are stripped.
    Values are converted to stripped strings.
    """
    if filters is None:
        return {}

    if not isinstance(filters, dict):
        raise InvalidFilterError("filters must be a dictionary.")

    normalized: dict[str, str] = {}

    for predicate, value in filters.items():
        predicate_text = str(predicate).strip()

        if predicate_text == "":
            raise InvalidFilterError("Filter predicate cannot be empty.")

        normalized[predicate_text] = normalize_filter_value(value)

    return normalized


# =============================================================================
# Path-building helpers
# =============================================================================

def build_filter_path(filters: dict[str, Any] | None) -> str:
    """
    Build the REST path section for predicate/value filters.

    Example:
        {"OBJECT_TYPE": "DEBRIS", "EPOCH": ">now-10"}

    becomes:
        /OBJECT_TYPE/DEBRIS/EPOCH/%3Enow-10
    """
    normalized = normalize_filters(filters)

    parts: list[str] = []

    for predicate, value in normalized.items():
        parts.append(encode_predicate_name(predicate))
        parts.append(encode_path_value(value))

    if not parts:
        return ""

    return "/" + "/".join(parts)


def build_predicates_path(predicates: list[str] | tuple[str, ...] | None) -> str:
    """
    Build the /predicates/... path segment.
    """
    if predicates is None:
        return ""

    return f"/predicates/{encode_predicates(predicates)}"


def build_orderby_path(orderby: str | None) -> str:
    """
    Build the /orderby/... path segment.
    """
    if orderby is None:
        return ""

    orderby_text = str(orderby).strip()

    if orderby_text == "":
        return ""

    return f"/orderby/{encode_orderby_value(orderby_text)}"


def build_limit_path(limit: int | None, offset: int | None = None) -> str:
    """
    Build the /limit/... path segment.

    Examples:
        limit=10, offset=None -> /limit/10
        limit=10, offset=5    -> /limit/10,5
    """
    if limit is None:
        if offset is not None:
            raise QueryBuilderError("offset cannot be provided without limit.")
        return ""

    if not isinstance(limit, int):
        raise QueryBuilderError("limit must be an integer.")

    if limit <= 0:
        raise QueryBuilderError("limit must be greater than zero.")

    if offset is None:
        return f"/limit/{limit}"

    if not isinstance(offset, int):
        raise QueryBuilderError("offset must be an integer.")

    if offset < 0:
        raise QueryBuilderError("offset cannot be negative.")

    return f"/limit/{limit},{offset}"


def build_format_path(output_format: str | None) -> str:
    """
    Build the /format/... path segment.

    Publicfiles raw download does not use a format segment.
    """
    if output_format is None:
        return ""

    fmt = output_format.strip().lower()

    if fmt == "" or fmt == "raw":
        return ""

    return f"/format/{quote(fmt, safe='')}"


def build_metadata_path(
    dataset_key: str,
    metadata: bool,
    output_format: str | None,
) -> str:
    """
    Build the /metadata/true path segment when supported.

    Space-Track ignores metadata for csv, tle, 3le, and kvn formats.
    """
    if not metadata:
        return ""

    if not dataset_supports_metadata(dataset_key, output_format):
        return ""

    return "/metadata/true"


def build_empty_result_path(show_empty: bool) -> str:
    """
    Build the /emptyresult/show path segment.
    """
    if not show_empty:
        return ""

    return "/emptyresult/show"


def build_favorites_path(favorites: str | None) -> str:
    """
    Build the /favorites/... path segment.
    """
    if favorites is None:
        return ""

    text = str(favorites).strip()

    if text == "":
        return ""

    return f"/favorites/{encode_path_value(text)}"


def build_distinct_path(distinct: bool) -> str:
    """
    Build the /distinct/true path segment.
    """
    if not distinct:
        return ""

    return "/distinct/true"


def normalize_raw_extra_path(raw_extra_path: str | None) -> str:
    """
    Normalize an optional raw extra path.

    This lets advanced users append a carefully prepared path segment.

    Example:
        "/COMMENTCODE/1"
    """
    if raw_extra_path is None:
        return ""

    text = str(raw_extra_path).strip()

    if text == "":
        return ""

    if not text.startswith("/"):
        text = "/" + text

    return text.rstrip("/")


# =============================================================================
# Dataset helpers
# =============================================================================

def get_dataset_config(dataset_key: str) -> DatasetConfig:
    """
    Return a DatasetConfig and convert KeyError into InvalidDatasetError.
    """
    try:
        return get_dataset(dataset_key)
    except KeyError as exc:
        raise InvalidDatasetError(str(exc)) from exc


def resolve_output_format(dataset_key: str, output_format: str | None) -> str:
    """
    Resolve and validate the output format for a dataset.

    If output_format is None, the dataset default is used.
    """
    dataset = get_dataset_config(dataset_key)

    fmt = output_format or dataset.default_format
    fmt = fmt.strip().lower()

    try:
        validate_dataset_format(dataset_key, fmt)
    except ValueError as exc:
        raise InvalidFormatError(str(exc)) from exc

    return fmt


def apply_recommended_filters(
    dataset_key: str,
    filters: dict[str, Any] | None,
    use_recommended: bool = False,
) -> dict[str, str]:
    """
    Merge recommended dataset filters with user filters.

    User-provided filters override recommended filters.
    Recommended filters are applied only when use_recommended=True.
    """
    user_filters = normalize_filters(filters)

    if not use_recommended:
        return user_filters

    recommended = get_recommended_filters(dataset_key)
    merged = dict(recommended)
    merged.update(user_filters)

    return merged


def ensure_publicfiles_download_name(query: SpaceTrackQuery) -> None:
    """
    Validate that publicfiles download requests have a download name.
    """
    if query.dataset_key != "publicfiles_download":
        return

    if not query.publicfiles_download_name:
        name_from_filters = query.filters.get("name")

        if not name_from_filters:
            raise QueryBuilderError(
                "publicfiles_download requires publicfiles_download_name "
                "or a filters['name'] value."
            )


# =============================================================================
# Main URL builders
# =============================================================================

def build_basicspacedata_url(
    dataset: DatasetConfig,
    filters: dict[str, Any] | None = None,
    output_format: str | None = None,
    predicates: list[str] | tuple[str, ...] | None = None,
    orderby: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    metadata: bool = False,
    show_empty: bool = False,
    favorites: str | None = None,
    distinct: bool = False,
    raw_extra_path: str | None = None,
    base_url: str = BASE_URL,
) -> str:
    """
    Build a URL for the basicspacedata controller.

    Example:
        https://www.space-track.org/basicspacedata/query/class/gp/DECAY_DATE/null-val/EPOCH/%3Enow-10/orderby/NORAD_CAT_ID/format/json
    """
    if dataset.controller != BASIC_SPACE_DATA_CONTROLLER:
        raise QueryBuilderError(
            f"Dataset {dataset.key!r} does not use the basicspacedata controller."
        )

    fmt = resolve_output_format(dataset.key, output_format)

    selected_orderby = orderby

    if selected_orderby is None:
        selected_orderby = dataset.default_orderby

    path = (
        f"/{dataset.controller}/{QUERY_ACTION}"
        f"/class/{encode_path_value(dataset.api_class)}"
        f"{build_filter_path(filters)}"
        f"{build_favorites_path(favorites)}"
        f"{build_predicates_path(predicates)}"
        f"{build_orderby_path(selected_orderby)}"
        f"{build_limit_path(limit, offset)}"
        f"{build_distinct_path(distinct)}"
        f"{build_metadata_path(dataset.key, metadata, fmt)}"
        f"{build_empty_result_path(show_empty)}"
        f"{normalize_raw_extra_path(raw_extra_path)}"
        f"{build_format_path(fmt)}"
    )

    return base_url.rstrip("/") + path


def build_publicfiles_url(
    dataset: DatasetConfig,
    filters: dict[str, Any] | None = None,
    publicfiles_download_name: str | None = None,
    base_url: str = BASE_URL,
) -> str:
    """
    Build a URL for the publicfiles controller.

    Supported examples:
        /publicfiles/query/class/dirs
        /publicfiles/query/class/files
        /publicfiles/query/class/loadpublicdata
        /publicfiles/query/class/download?name=LINK
    """
    if dataset.controller != PUBLIC_FILES_CONTROLLER:
        raise QueryBuilderError(
            f"Dataset {dataset.key!r} does not use the publicfiles controller."
        )

    path = (
        f"/{dataset.controller}/{QUERY_ACTION}"
        f"/class/{encode_path_value(dataset.api_class)}"
    )

    url = base_url.rstrip("/") + path

    if dataset.api_class == "download":
        normalized_filters = normalize_filters(filters)
        name = publicfiles_download_name or normalized_filters.get("name")

        if not name:
            raise QueryBuilderError(
                "Public file download requires a file name or LINK value."
            )

        query_string = urlencode({"name": name})

        return f"{url}?{query_string}"

    return url


def build_query_url(
    dataset_key: str,
    filters: dict[str, Any] | None = None,
    output_format: str | None = None,
    predicates: list[str] | tuple[str, ...] | None = None,
    orderby: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    metadata: bool = False,
    show_empty: bool = False,
    favorites: str | None = None,
    distinct: bool = False,
    raw_extra_path: str | None = None,
    publicfiles_download_name: str | None = None,
    use_recommended_filters: bool = False,
    base_url: str = BASE_URL,
) -> str:
    """
    Build a complete Space-Track query URL.

    Args:
        dataset_key:
            Key from DATASETS.

        filters:
            Predicate/value filters.

        output_format:
            Output format. If None, the dataset default is used.

        predicates:
            Optional list of predicates to return.

        orderby:
            Optional orderby predicate. If None, dataset default_orderby is used.

        limit:
            Optional result limit.

        offset:
            Optional result offset.

        metadata:
            Whether to request metadata where supported.

        show_empty:
            Whether to show "NO RESULTS RETURNED" for empty results.

        favorites:
            Optional favorites list.

        distinct:
            Whether to request distinct rows.

        raw_extra_path:
            Advanced raw path segment appended before format.

        publicfiles_download_name:
            Name/LINK used by the publicfiles download endpoint.

        use_recommended_filters:
            Whether to include recommended filters from dataset_configs.py.

        base_url:
            Base Space-Track URL.

    Returns:
        Full query URL as a string.
    """
    dataset = get_dataset_config(dataset_key)

    merged_filters = apply_recommended_filters(
        dataset_key=dataset_key,
        filters=filters,
        use_recommended=use_recommended_filters,
    )

    if dataset_uses_publicfiles_controller(dataset_key):
        return build_publicfiles_url(
            dataset=dataset,
            filters=merged_filters,
            publicfiles_download_name=publicfiles_download_name,
            base_url=base_url,
        )

    return build_basicspacedata_url(
        dataset=dataset,
        filters=merged_filters,
        output_format=output_format,
        predicates=predicates,
        orderby=orderby,
        limit=limit,
        offset=offset,
        metadata=metadata,
        show_empty=show_empty,
        favorites=favorites,
        distinct=distinct,
        raw_extra_path=raw_extra_path,
        base_url=base_url,
    )


def build_query_url_from_object(
    query: SpaceTrackQuery,
    use_recommended_filters: bool = False,
    base_url: str = BASE_URL,
) -> str:
    """
    Build a query URL from a SpaceTrackQuery object.
    """
    ensure_publicfiles_download_name(query)

    return build_query_url(
        dataset_key=query.dataset_key,
        filters=query.filters,
        output_format=query.output_format,
        predicates=query.predicates,
        orderby=query.orderby,
        limit=query.limit,
        offset=query.offset,
        metadata=query.metadata,
        show_empty=query.show_empty,
        favorites=query.favorites,
        distinct=query.distinct,
        raw_extra_path=query.raw_extra_path,
        publicfiles_download_name=query.publicfiles_download_name,
        use_recommended_filters=use_recommended_filters,
        base_url=base_url,
    )


# =============================================================================
# Model definition URL builders
# =============================================================================

def build_modeldef_url(
    dataset_key: str,
    base_url: str = BASE_URL,
) -> str:
    """
    Build a modeldef URL for a dataset.

    Example:
        https://www.space-track.org/basicspacedata/modeldef/class/gp

    Model definitions are useful for discovering valid predicates.
    They should be cached and not requested before every query.
    """
    dataset = get_dataset_config(dataset_key)

    if dataset.controller != BASIC_SPACE_DATA_CONTROLLER:
        raise QueryBuilderError(
            "Model definitions are only supported here for basicspacedata datasets."
        )

    path = (
        f"/{dataset.controller}/{MODELDEF_ACTION}"
        f"/class/{encode_path_value(dataset.api_class)}"
    )

    return base_url.rstrip("/") + path


def build_modeldef_url_for_class(
    api_class: str,
    controller: str = BASIC_SPACE_DATA_CONTROLLER,
    base_url: str = BASE_URL,
) -> str:
    """
    Build a modeldef URL directly from a Space-Track class name.

    Example:
        build_modeldef_url_for_class("gp")
    """
    api_class_text = str(api_class).strip()

    if api_class_text == "":
        raise QueryBuilderError("api_class cannot be empty.")

    controller_text = str(controller).strip()

    if controller_text == "":
        raise QueryBuilderError("controller cannot be empty.")

    path = (
        f"/{encode_path_value(controller_text)}"
        f"/{MODELDEF_ACTION}"
        f"/class/{encode_path_value(api_class_text)}"
    )

    return base_url.rstrip("/") + path


# =============================================================================
# Query preview / debugging helpers
# =============================================================================

def build_relative_query_path(url: str, base_url: str = BASE_URL) -> str:
    """
    Convert a full URL into a relative path if it starts with base_url.

    This is useful for displaying cleaner query previews.
    """
    clean_base = base_url.rstrip("/")

    if url.startswith(clean_base):
        return url[len(clean_base):]

    return url


def summarize_query(
    dataset_key: str,
    filters: dict[str, Any] | None = None,
    output_format: str | None = None,
    predicates: list[str] | tuple[str, ...] | None = None,
    orderby: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    metadata: bool = False,
    show_empty: bool = False,
    favorites: str | None = None,
    distinct: bool = False,
    raw_extra_path: str | None = None,
    publicfiles_download_name: str | None = None,
    use_recommended_filters: bool = False,
) -> dict[str, Any]:
    """
    Return a dictionary summary of a query.

    This is intended for previews and metadata writing.
    """
    dataset = get_dataset_config(dataset_key)

    resolved_format = (
        "raw"
        if dataset_uses_publicfiles_controller(dataset_key)
        and dataset.api_class == "download"
        else resolve_output_format(dataset_key, output_format)
    )

    merged_filters = apply_recommended_filters(
        dataset_key=dataset_key,
        filters=filters,
        use_recommended=use_recommended_filters,
    )

    url = build_query_url(
        dataset_key=dataset_key,
        filters=merged_filters,
        output_format=resolved_format,
        predicates=predicates,
        orderby=orderby,
        limit=limit,
        offset=offset,
        metadata=metadata,
        show_empty=show_empty,
        favorites=favorites,
        distinct=distinct,
        raw_extra_path=raw_extra_path,
        publicfiles_download_name=publicfiles_download_name,
    )

    return {
        "dataset_key": dataset.key,
        "dataset_label": dataset.label,
        "controller": dataset.controller,
        "api_class": dataset.api_class,
        "filters": merged_filters,
        "output_format": resolved_format,
        "predicates": list(predicates) if predicates else None,
        "orderby": orderby if orderby is not None else get_default_orderby(dataset_key),
        "limit": limit,
        "offset": offset,
        "metadata_requested": metadata,
        "metadata_supported": dataset_supports_metadata(dataset_key, resolved_format),
        "show_empty": show_empty,
        "favorites": favorites,
        "distinct": distinct,
        "raw_extra_path": raw_extra_path,
        "publicfiles_download_name": publicfiles_download_name,
        "use_recommended_filters": use_recommended_filters,
        "url": url,
        "relative_path": build_relative_query_path(url),
    }


def print_query_summary(summary: dict[str, Any]) -> None:
    """
    Print a human-readable query summary.
    """
    print("\n" + "=" * 72)
    print("SPACE-TRACK QUERY SUMMARY")
    print("=" * 72)

    print(f"Dataset      : {summary['dataset_label']}")
    print(f"Dataset key  : {summary['dataset_key']}")
    print(f"Controller   : {summary['controller']}")
    print(f"API class    : {summary['api_class']}")
    print(f"Format       : {summary['output_format']}")

    if summary.get("favorites"):
        print(f"Favorites    : {summary['favorites']}")

    if summary.get("orderby"):
        print(f"Order by     : {summary['orderby']}")

    if summary.get("limit") is not None:
        if summary.get("offset") is not None:
            print(f"Limit        : {summary['limit']}, offset {summary['offset']}")
        else:
            print(f"Limit        : {summary['limit']}")

    if summary.get("metadata_requested"):
        print(f"Metadata     : requested, supported={summary['metadata_supported']}")
    else:
        print("Metadata     : not requested")

    if summary.get("show_empty"):
        print("Empty result : show")

    if summary.get("distinct"):
        print("Distinct     : true")

    filters = summary.get("filters") or {}

    if filters:
        print("\nFilters:")
        for predicate, value in filters.items():
            print(f"  - {predicate}: {value}")
    else:
        print("\nFilters      : none")

    if summary.get("predicates"):
        print("\nReturned predicates:")
        for predicate in summary["predicates"]:
            print(f"  - {predicate}")

    print("\nRelative path:")
    print(summary["relative_path"])

    print("\nFull URL:")
    print(summary["url"])

    print("=" * 72)


# =============================================================================
# Convenience builders for common workflows
# =============================================================================

def build_latest_gp_url(
    object_type: str | None = None,
    on_orbit_only: bool = True,
    epoch_days: int | None = 10,
    output_format: str = "json",
    orderby: str = "NORAD_CAT_ID",
    limit: int | None = None,
) -> str:
    """
    Convenience builder for latest GP data.

    Args:
        object_type:
            Optional object type such as PAYLOAD, DEBRIS, ROCKET BODY, UNKNOWN.

        on_orbit_only:
            Adds DECAY_DATE/null-val when True.

        epoch_days:
            Adds EPOCH/>now-{epoch_days}. Use None to skip.

        output_format:
            json, csv, xml, kvn, html, tle, or 3le.

        orderby:
            Orderby value.

        limit:
            Optional limit.
    """
    filters: dict[str, str] = {}

    if object_type:
        filters["OBJECT_TYPE"] = object_type

    if on_orbit_only:
        filters["DECAY_DATE"] = "null-val"

    if epoch_days is not None:
        if epoch_days <= 0:
            raise QueryBuilderError("epoch_days must be greater than zero.")
        filters["EPOCH"] = f">now-{epoch_days}"

    return build_query_url(
        dataset_key="gp",
        filters=filters,
        output_format=output_format,
        orderby=orderby,
        limit=limit,
    )


def build_satcat_url(
    current_only: bool = True,
    output_format: str = "json",
    orderby: str = "NORAD_CAT_ID",
    limit: int | None = None,
) -> str:
    """
    Convenience builder for SATCAT data.
    """
    filters: dict[str, str] = {}

    if current_only:
        filters["CURRENT"] = "Y"

    return build_query_url(
        dataset_key="satcat",
        filters=filters,
        output_format=output_format,
        orderby=orderby,
        limit=limit,
    )


def build_decay_url(
    recent_msg_days: int | None = None,
    output_format: str = "json",
    orderby: str = "DECAY_EPOCH desc",
    limit: int | None = None,
) -> str:
    """
    Convenience builder for decay data.
    """
    filters: dict[str, str] = {}

    if recent_msg_days is not None:
        if recent_msg_days <= 0:
            raise QueryBuilderError("recent_msg_days must be greater than zero.")
        filters["MSG_EPOCH"] = f">now-{recent_msg_days}"

    return build_query_url(
        dataset_key="decay",
        filters=filters,
        output_format=output_format,
        orderby=orderby,
        limit=limit,
    )


def build_cdm_public_url(
    created_days: int | None = 1,
    output_format: str = "json",
    orderby: str = "CREATED desc",
    limit: int | None = None,
) -> str:
    """
    Convenience builder for public conjunction data.
    """
    filters: dict[str, str] = {}

    if created_days is not None:
        if created_days <= 0:
            raise QueryBuilderError("created_days must be greater than zero.")
        filters["CREATED"] = f">now-{created_days}"

    return build_query_url(
        dataset_key="cdm_public",
        filters=filters,
        output_format=output_format,
        orderby=orderby,
        limit=limit,
    )


# =============================================================================
# Self-test
# =============================================================================

def _self_test() -> None:
    """
    Run a few basic URL-building checks.

    This is not a replacement for formal tests, but it is useful while developing.
    """
    examples = [
        build_latest_gp_url(object_type="DEBRIS", output_format="json"),
        build_latest_gp_url(object_type="PAYLOAD", output_format="tle", limit=5),
        build_satcat_url(output_format="csv", limit=10),
        build_decay_url(recent_msg_days=1, output_format="json"),
        build_cdm_public_url(created_days=1, output_format="json"),
        build_query_url("boxscore", output_format="csv"),
        build_query_url("publicfiles_loadpublicdata"),
        build_query_url(
            "publicfiles_download",
            publicfiles_download_name="example_file.zip",
        ),
        build_modeldef_url("gp"),
    ]

    print("\nQuery builder self-test examples:")

    for url in examples:
        print(f"  {url}")


if __name__ == "__main__":
    _self_test()