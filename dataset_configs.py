"""
dataset_configs.py

Configuration definitions for the Space-Track Data Downloader.

This file contains user-facing dataset menus, Space-Track API class mappings,
supported output formats, common filters, object-type presets, orbit-regime
presets, and helper functions used by the interactive CLI.

This file does not make network requests. It only describes what the downloader
can query.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# =============================================================================
# Space-Track controllers
# =============================================================================

BASIC_SPACE_DATA_CONTROLLER = "basicspacedata"
PUBLIC_FILES_CONTROLLER = "publicfiles"


# =============================================================================
# Supported output formats
# =============================================================================

FORMAT_DESCRIPTIONS: dict[str, str] = {
    "json": "JSON - recommended for programming and structured processing",
    "csv": "CSV - recommended for spreadsheets and analysis",
    "xml": "XML - OMM-compatible structured format where supported",
    "kvn": "KVN - key-value notation where supported",
    "html": "HTML - useful for quick human-readable inspection",
    "tle": "TLE - legacy 2-line element format",
    "3le": "3LE - legacy 3-line element format with object name",
}

TEXT_FORMATS: set[str] = {
    "tle",
    "3le",
    "xml",
    "kvn",
    "html",
}

STRUCTURED_FORMATS: set[str] = {
    "json",
    "csv",
}


# =============================================================================
# Common object types
# =============================================================================

OBJECT_TYPE_FILTERS: dict[str, dict[str, Any]] = {
    "active_payloads": {
        "label": "Active payloads",
        "description": "Payload objects currently in orbit",
        "filters": {
            "OBJECT_TYPE": "PAYLOAD",
            "DECAY_DATE": "null-val",
        },
    },
    "payloads_all": {
        "label": "All payloads",
        "description": "Payload objects including decayed payloads",
        "filters": {
            "OBJECT_TYPE": "PAYLOAD",
        },
    },
    "analyst_objects": {
        "label": "Analyst objects",
        "description": (
            "Objects tracked by the Space Surveillance Network but not fully "
            "associated with public SATCAT metadata"
        ),
        "filters": {
            "NORAD_CAT_ID": "80000--89999",
            "DECAY_DATE": "null-val",
        },
    },
    "space_fence_analyst_objects": {
        "label": "Space Fence analyst objects",
        "description": (
            "Analyst objects commonly maintained in the Space Fence range"
        ),
        "filters": {
            "NORAD_CAT_ID": "270000--339999",
            "DECAY_DATE": "null-val",
        },
    },
    "debris_on_orbit": {
        "label": "Debris currently in orbit",
        "description": "Debris objects that have not decayed",
        "filters": {
            "OBJECT_TYPE": "DEBRIS",
            "DECAY_DATE": "null-val",
        },
    },
    "debris_all": {
        "label": "All debris",
        "description": "Debris objects including decayed debris",
        "filters": {
            "OBJECT_TYPE": "DEBRIS",
        },
    },
    "rocket_bodies_on_orbit": {
        "label": "Rocket bodies currently in orbit",
        "description": "Rocket bodies that have not decayed",
        "filters": {
            "OBJECT_TYPE": "ROCKET BODY",
            "DECAY_DATE": "null-val",
        },
    },
    "rocket_bodies_all": {
        "label": "All rocket bodies",
        "description": "Rocket bodies including decayed rocket bodies",
        "filters": {
            "OBJECT_TYPE": "ROCKET BODY",
        },
    },
    "unknown_on_orbit": {
        "label": "Unknown objects currently in orbit",
        "description": "Unknown object types that have not decayed",
        "filters": {
            "OBJECT_TYPE": "UNKNOWN",
            "DECAY_DATE": "null-val",
        },
    },
    "unknown_all": {
        "label": "All unknown objects",
        "description": "Unknown object types including decayed objects",
        "filters": {
            "OBJECT_TYPE": "UNKNOWN",
        },
    },
    "all_on_orbit": {
        "label": "All objects currently in orbit",
        "description": "All object types that have not decayed",
        "filters": {
            "DECAY_DATE": "null-val",
        },
    },
    "all_objects": {
        "label": "All catalog objects",
        "description": "All object types including decayed objects",
        "filters": {},
    },
}


# =============================================================================
# Orbit regime presets
# =============================================================================

ORBIT_REGIME_FILTERS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "All orbit regimes",
        "description": "No orbit-regime filter",
        "filters": {},
    },
    "leo_perigee": {
        "label": "LEO - Low Earth Orbit by perigee",
        "description": "Objects with perigee below 2,000 km",
        "filters": {
            "PERIGEE": "<2000",
        },
    },
    "leo_mean_motion": {
        "label": "LEO - Low Earth Orbit by mean motion",
        "description": "Objects with mean motion greater than 11.25 rev/day",
        "filters": {
            "MEAN_MOTION": ">11.25",
        },
    },
    "meo": {
        "label": "MEO - Medium Earth Orbit",
        "description": "Objects with perigee between 2,000 km and 35,586 km",
        "filters": {
            "PERIGEE": "2000--35586",
        },
    },
    "geo_period": {
        "label": "GEO - Geosynchronous by orbital period",
        "description": "Objects with period between 1,430 and 1,450 minutes",
        "filters": {
            "PERIOD": "1430--1450",
        },
    },
    "geo_mean_motion": {
        "label": "GEO - Geosynchronous by mean motion",
        "description": (
            "Objects with mean motion between 0.99 and 1.01 rev/day "
            "and eccentricity below 0.01"
        ),
        "filters": {
            "MEAN_MOTION": "0.99--1.01",
            "ECCENTRICITY": "<0.01",
        },
    },
    "heo": {
        "label": "HEO - Highly Elliptical Orbit",
        "description": "Objects with eccentricity greater than 0.25",
        "filters": {
            "ECCENTRICITY": ">0.25",
        },
    },
}


# =============================================================================
# RCS size presets
# =============================================================================

RCS_SIZE_FILTERS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "All RCS sizes",
        "description": "No radar cross-section size filter",
        "filters": {},
    },
    "small": {
        "label": "Small RCS",
        "description": "Small radar cross-section objects",
        "filters": {
            "RCS_SIZE": "SMALL",
        },
    },
    "medium": {
        "label": "Medium RCS",
        "description": "Medium radar cross-section objects",
        "filters": {
            "RCS_SIZE": "MEDIUM",
        },
    },
    "large": {
        "label": "Large RCS",
        "description": "Large radar cross-section objects",
        "filters": {
            "RCS_SIZE": "LARGE",
        },
    },
}


# =============================================================================
# Epoch recency presets
# =============================================================================

EPOCH_RECENCY_FILTERS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "All epochs",
        "description": "No epoch recency filter",
        "filters": {},
    },
    "1": {
        "label": "Last 1 day",
        "description": "Only records with EPOCH newer than now minus 1 day",
        "filters": {
            "EPOCH": ">now-1",
        },
    },
    "7": {
        "label": "Last 7 days",
        "description": "Only records with EPOCH newer than now minus 7 days",
        "filters": {
            "EPOCH": ">now-7",
        },
    },
    "10": {
        "label": "Last 10 days",
        "description": "Recommended for newest propagable GP element sets",
        "filters": {
            "EPOCH": ">now-10",
        },
    },
    "30": {
        "label": "Last 30 days",
        "description": "Only records with EPOCH newer than now minus 30 days",
        "filters": {
            "EPOCH": ">now-30",
        },
    },
    "90": {
        "label": "Last 90 days",
        "description": "Only records with EPOCH newer than now minus 90 days",
        "filters": {
            "EPOCH": ">now-90",
        },
    },
    "180": {
        "label": "Last 180 days",
        "description": "Only records with EPOCH newer than now minus 180 days",
        "filters": {
            "EPOCH": ">now-180",
        },
    },
    "365": {
        "label": "Last 365 days",
        "description": "Only records with EPOCH newer than now minus 365 days",
        "filters": {
            "EPOCH": ">now-365",
        },
    },
}


# =============================================================================
# Creation-date recency presets
# =============================================================================

CREATION_DATE_RECENCY_FILTERS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "All creation dates",
        "description": "No creation-date recency filter",
        "filters": {},
    },
    "1_hour": {
        "label": "Created in the last 1 hour",
        "description": "CREATION_DATE newer than now minus 0.042 days",
        "filters": {
            "CREATION_DATE": ">now-0.042",
        },
    },
    "8_hours": {
        "label": "Created in the last 8 hours",
        "description": "CREATION_DATE newer than now minus 0.333 days",
        "filters": {
            "CREATION_DATE": ">now-0.333",
        },
    },
    "1_day": {
        "label": "Created in the last 1 day",
        "description": "CREATION_DATE newer than now minus 1 day",
        "filters": {
            "CREATION_DATE": ">now-1",
        },
    },
    "7_days": {
        "label": "Created in the last 7 days",
        "description": "CREATION_DATE newer than now minus 7 days",
        "filters": {
            "CREATION_DATE": ">now-7",
        },
    },
    "30_days": {
        "label": "Created in the last 30 days",
        "description": "CREATION_DATE newer than now minus 30 days",
        "filters": {
            "CREATION_DATE": ">now-30",
        },
    },
}


# =============================================================================
# Country presets
# =============================================================================

COUNTRY_PRESETS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "All countries / owners",
        "value": None,
    },
    "US": {
        "label": "United States",
        "value": "US",
    },
    "CIS": {
        "label": "Commonwealth of Independent States / Russia",
        "value": "CIS",
    },
    "PRC": {
        "label": "People's Republic of China",
        "value": "PRC",
    },
    "IND": {
        "label": "India",
        "value": "IND",
    },
    "JPN": {
        "label": "Japan",
        "value": "JPN",
    },
    "ESA": {
        "label": "European Space Agency",
        "value": "ESA",
    },
    "UK": {
        "label": "United Kingdom",
        "value": "UK",
    },
    "FR": {
        "label": "France",
        "value": "FR",
    },
    "GER": {
        "label": "Germany",
        "value": "GER",
    },
    "custom": {
        "label": "Enter a custom country code",
        "value": "custom",
    },
}


# =============================================================================
# Favorites presets
# =============================================================================

FAVORITES_PRESETS: dict[str, dict[str, Any]] = {
    "all": {
        "label": "All configured favorites",
        "value": "All",
    },
    "my_favorites": {
        "label": "My favorites",
        "value": "my_favorites",
    },
    "geosynchronous": {
        "label": "Geosynchronous",
        "value": "Geosynchronous",
    },
    "navigation": {
        "label": "Navigation",
        "value": "Navigation",
    },
    "special_interest": {
        "label": "Special Interest",
        "value": "Special_Interest",
    },
    "visible": {
        "label": "Visible",
        "value": "Visible",
    },
    "weather": {
        "label": "Weather",
        "value": "Weather",
    },
    "amateur": {
        "label": "Amateur",
        "value": "Amateur",
    },
}


# =============================================================================
# Dataset definitions
# =============================================================================

@dataclass(frozen=True)
class DatasetConfig:
    """
    A Space-Track dataset exposed through the downloader.

    Attributes:
        key:
            Internal key used by the downloader.

        label:
            Human-readable name shown in menus.

        description:
            Short explanation shown to the user.

        controller:
            Space-Track request controller, such as "basicspacedata" or
            "publicfiles".

        api_class:
            Space-Track request class, such as "gp" or "satcat".
            For publicfiles download endpoints, this can be "download",
            "files", "dirs", or "loadpublicdata".

        default_format:
            Default output format.

        supported_formats:
            Output formats supported by this dataset.

        default_orderby:
            Default Space-Track orderby predicate.

        common_filters:
            Common predicates that should be offered in normal mode.

        recommended_filters:
            Filters that are recommended by default for safe/efficient querying.

        notes:
            Additional warnings or usage guidance.

        allow_tle_formats:
            Whether this dataset supports TLE/3LE output.

        supports_metadata:
            Whether metadata/true is meaningful for this dataset.

        requires_login:
            Whether authentication is required.

        is_publicfiles_endpoint:
            Whether this dataset uses the publicfiles controller.
    """

    key: str
    label: str
    description: str
    controller: str
    api_class: str
    default_format: str
    supported_formats: tuple[str, ...]
    default_orderby: str | None
    common_filters: tuple[str, ...]
    recommended_filters: dict[str, str]
    notes: tuple[str, ...]
    allow_tle_formats: bool = False
    supports_metadata: bool = True
    requires_login: bool = True
    is_publicfiles_endpoint: bool = False


DATASETS: dict[str, DatasetConfig] = {
    "gp": DatasetConfig(
        key="gp",
        label="Latest ELSET / GP data",
        description=(
            "Newest general perturbations element set for each tracked "
            "earth-orbiting object."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="gp",
        default_format="json",
        supported_formats=("json", "csv", "xml", "kvn", "html", "tle", "3le"),
        default_orderby="NORAD_CAT_ID",
        common_filters=(
            "NORAD_CAT_ID",
            "OBJECT_NAME",
            "OBJECT_TYPE",
            "COUNTRY_CODE",
            "SITE",
            "LAUNCH_DATE",
            "DECAY_DATE",
            "PERIOD",
            "INCLINATION",
            "APOGEE",
            "PERIGEE",
            "ECCENTRICITY",
            "MEAN_MOTION",
            "RCS_SIZE",
            "EPOCH",
            "CREATION_DATE",
            "FILE",
            "GP_ID",
        ),
        recommended_filters={
            "DECAY_DATE": "null-val",
            "EPOCH": ">now-10",
        },
        notes=(
            "Use this class for current/latest ephemerides.",
            "For propagable on-orbit objects, DECAY_DATE/null-val and recent EPOCH are recommended.",
            "For expanded catalog compatibility, JSON, CSV, XML, or KVN are preferred over legacy TLE/3LE.",
        ),
        allow_tle_formats=True,
        supports_metadata=True,
    ),
    "gp_history": DatasetConfig(
        key="gp_history",
        label="Historical ELSET / GP history data",
        description=(
            "Historical general perturbations element sets. Use carefully and "
            "limit by object ID and short date ranges."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="gp_history",
        default_format="json",
        supported_formats=("json", "csv", "xml", "kvn", "html", "tle", "3le"),
        default_orderby="EPOCH desc",
        common_filters=(
            "NORAD_CAT_ID",
            "OBJECT_NAME",
            "OBJECT_TYPE",
            "COUNTRY_CODE",
            "EPOCH",
            "CREATION_DATE",
            "FILE",
            "GP_ID",
            "PERIOD",
            "INCLINATION",
            "APOGEE",
            "PERIGEE",
            "ECCENTRICITY",
            "MEAN_MOTION",
        ),
        recommended_filters={},
        notes=(
            "Do not use this class for current ephemerides; use GP instead.",
            "Always limit historical queries by NORAD_CAT_ID and a short EPOCH or CREATION_DATE range.",
            "Large gp_history queries can be slow or rejected.",
        ),
        allow_tle_formats=True,
        supports_metadata=True,
    ),
    "satcat": DatasetConfig(
        key="satcat",
        label="Satellite Catalog / SATCAT",
        description=(
            "Authoritative satellite catalog metadata including object name, "
            "country, launch, decay, site, period, apogee, perigee, and status."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="satcat",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="NORAD_CAT_ID",
        common_filters=(
            "NORAD_CAT_ID",
            "SATNAME",
            "INTLDES",
            "OBJECT_TYPE",
            "COUNTRY",
            "LAUNCH",
            "SITE",
            "DECAY",
            "PERIOD",
            "INCLINATION",
            "APOGEE",
            "PERIGEE",
            "RCS",
            "CURRENT",
            "COMMENTCODE",
            "FILE",
        ),
        recommended_filters={
            "CURRENT": "Y",
        },
        notes=(
            "Use this class for catalog metadata rather than orbital propagation.",
            "SATCAT should not be queried too frequently in automated workflows.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "satcat_change": DatasetConfig(
        key="satcat_change",
        label="SATCAT changes",
        description=(
            "Recent SATCAT changes for objects with updates to identifiers, "
            "names, country, launch, or decay fields."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="satcat_change",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="CHANGE_DATE desc",
        common_filters=(
            "NORAD_CAT_ID",
            "SATNAME",
            "INTLDES",
            "COUNTRY",
            "LAUNCH",
            "DECAY",
            "CHANGE_DATE",
        ),
        recommended_filters={},
        notes=(
            "Useful for monitoring recent catalog changes.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "satcat_debut": DatasetConfig(
        key="satcat_debut",
        label="SATCAT debut / new catalog records",
        description="Records newly added to the satellite catalog.",
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="satcat_debut",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="DEBUT desc",
        common_filters=(
            "NORAD_CAT_ID",
            "SATNAME",
            "INTLDES",
            "COUNTRY",
            "LAUNCH",
            "DEBUT",
        ),
        recommended_filters={
            "DEBUT": ">now-1",
        },
        notes=(
            "Useful for retrieving objects added to the catalog recently.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "decay": DatasetConfig(
        key="decay",
        label="Decay / reentry data",
        description=(
            "Predicted and historical decay information, including decay "
            "lifecycle records."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="decay",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="DECAY_EPOCH desc",
        common_filters=(
            "NORAD_CAT_ID",
            "OBJECT_NAME",
            "INTLDES",
            "COUNTRY_CODE",
            "MSG_EPOCH",
            "DECAY_EPOCH",
            "PRECEDENCE",
            "SOURCE",
            "RCS_SIZE",
            "FILE",
        ),
        recommended_filters={},
        notes=(
            "Use this class for historical and predicted decay messages.",
            "For routine checks, use recent MSG_EPOCH or DECAY_EPOCH filters.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "tip": DatasetConfig(
        key="tip",
        label="TIP messages",
        description=(
            "Tracking and Impact Prediction messages for selected object reentries."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="tip",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="MSG_EPOCH desc",
        common_filters=(
            "NORAD_CAT_ID",
            "OBJECT_NUMBER",
            "MSG_EPOCH",
            "INSERT_EPOCH",
            "DECAY_EPOCH",
            "WINDOW",
            "LAT",
            "LON",
            "INCL",
            "NEXT_REPORT",
            "HIGH_INTEREST",
            "ID",
        ),
        recommended_filters={
            "INSERT_EPOCH": ">now-0.042",
        },
        notes=(
            "TIP messages may be updated more frequently near reentry.",
            "Use recent INSERT_EPOCH filters for periodic monitoring.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "cdm_public": DatasetConfig(
        key="cdm_public",
        label="Public conjunction data / CDM",
        description="Publicly available conjunction data messages.",
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="cdm_public",
        default_format="json",
        supported_formats=("json", "csv", "xml", "kvn", "html"),
        default_orderby="CREATED desc",
        common_filters=(
            "CDM_ID",
            "CREATED",
            "TCA",
            "MIN_RNG",
            "PC",
            "SAT_1_ID",
            "SAT_1_NAME",
            "SAT1_OBJECT_TYPE",
            "SAT1_RCS",
            "SAT_2_ID",
            "SAT_2_NAME",
            "SAT2_OBJECT_TYPE",
            "SAT2_RCS",
            "EMERGENCY_REPORTABLE",
        ),
        recommended_filters={
            "CREATED": ">now-1",
        },
        notes=(
            "Use CREATED filters for recent public conjunction messages.",
            "TCA is the predicted time of closest approach.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "boxscore": DatasetConfig(
        key="boxscore",
        label="Box Score / country totals",
        description=(
            "Summary accounting of objects grouped by country or organization."
        ),
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="boxscore",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="COUNTRY",
        common_filters=(
            "COUNTRY",
            "SPADOC_CD",
            "ORBITAL_TBA",
            "ORBITAL_PAYLOAD_COUNT",
            "ORBITAL_ROCKET_BODY_COUNT",
            "ORBITAL_DEBRIS_COUNT",
            "ORBITAL_TOTAL_COUNT",
            "DECAYED_PAYLOAD_COUNT",
            "DECAYED_ROCKET_BODY_COUNT",
            "DECAYED_DEBRIS_COUNT",
            "DECAYED_TOTAL_COUNT",
            "COUNTRY_TOTAL",
        ),
        recommended_filters={},
        notes=(
            "Use this class for summary counts rather than individual objects.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "launch_site": DatasetConfig(
        key="launch_site",
        label="Launch site reference data",
        description="Reference list of launch sites found in SATCAT records.",
        controller=BASIC_SPACE_DATA_CONTROLLER,
        api_class="launch_site",
        default_format="json",
        supported_formats=("json", "csv", "xml", "html"),
        default_orderby="SITE_CODE",
        common_filters=(
            "SITE_CODE",
            "LAUNCH_SITE",
        ),
        recommended_filters={},
        notes=(
            "Useful for looking up launch site codes.",
        ),
        allow_tle_formats=False,
        supports_metadata=True,
    ),
    "publicfiles_dirs": DatasetConfig(
        key="publicfiles_dirs",
        label="Public files - list directories",
        description="List directories that contain public Space-Track files.",
        controller=PUBLIC_FILES_CONTROLLER,
        api_class="dirs",
        default_format="json",
        supported_formats=("json",),
        default_orderby=None,
        common_filters=(),
        recommended_filters={},
        notes=(
            "Uses the publicfiles controller rather than basicspacedata.",
        ),
        allow_tle_formats=False,
        supports_metadata=False,
        requires_login=True,
        is_publicfiles_endpoint=True,
    ),
    "publicfiles_files": DatasetConfig(
        key="publicfiles_files",
        label="Public files - list files",
        description="List public files available for download.",
        controller=PUBLIC_FILES_CONTROLLER,
        api_class="files",
        default_format="json",
        supported_formats=("json",),
        default_orderby=None,
        common_filters=(),
        recommended_filters={},
        notes=(
            "Uses the publicfiles controller rather than basicspacedata.",
        ),
        allow_tle_formats=False,
        supports_metadata=False,
        requires_login=True,
        is_publicfiles_endpoint=True,
    ),
    "publicfiles_loadpublicdata": DatasetConfig(
        key="publicfiles_loadpublicdata",
        label="Public files - detailed file metadata",
        description=(
            "Return detailed public file metadata including source, type, date, "
            "link, name, and size."
        ),
        controller=PUBLIC_FILES_CONTROLLER,
        api_class="loadpublicdata",
        default_format="json",
        supported_formats=("json",),
        default_orderby=None,
        common_filters=(),
        recommended_filters={},
        notes=(
            "Use this before downloading a public file.",
            "The LINK field is used as the download name.",
        ),
        allow_tle_formats=False,
        supports_metadata=False,
        requires_login=True,
        is_publicfiles_endpoint=True,
    ),
    "publicfiles_download": DatasetConfig(
        key="publicfiles_download",
        label="Public files - download selected file",
        description="Download a selected public file by its LINK/name value.",
        controller=PUBLIC_FILES_CONTROLLER,
        api_class="download",
        default_format="raw",
        supported_formats=("raw",),
        default_orderby=None,
        common_filters=(
            "name",
        ),
        recommended_filters={},
        notes=(
            "This endpoint requires a file name or LINK value.",
        ),
        allow_tle_formats=False,
        supports_metadata=False,
        requires_login=True,
        is_publicfiles_endpoint=True,
    ),
}


# =============================================================================
# Menu groups
# =============================================================================

DATASET_GROUPS: dict[str, dict[str, Any]] = {
    "object_elset": {
        "label": "Object / ELSET data",
        "description": "Current and historical orbital element data",
        "datasets": (
            "gp",
            "gp_history",
        ),
    },
    "catalog": {
        "label": "Satellite catalog data",
        "description": "SATCAT records, changes, debut records, and launch sites",
        "datasets": (
            "satcat",
            "satcat_change",
            "satcat_debut",
            "launch_site",
        ),
    },
    "decay_reentry": {
        "label": "Decay / Reentry data",
        "description": "Decay records and TIP messages",
        "datasets": (
            "decay",
            "tip",
        ),
    },
    "conjunctions": {
        "label": "Conjunction data",
        "description": "Public conjunction data messages",
        "datasets": (
            "cdm_public",
        ),
    },
    "summary": {
        "label": "Summary / reports",
        "description": "Box score and aggregate object counts",
        "datasets": (
            "boxscore",
        ),
    },
    "publicfiles": {
        "label": "Public files",
        "description": "List and download files from the publicfiles endpoint",
        "datasets": (
            "publicfiles_dirs",
            "publicfiles_files",
            "publicfiles_loadpublicdata",
            "publicfiles_download",
        ),
    },
}


# =============================================================================
# Advanced query operators
# =============================================================================

REST_OPERATORS: dict[str, dict[str, str]] = {
    "equals": {
        "label": "Equals",
        "symbol": "",
        "example": "NORAD_CAT_ID/25544",
    },
    "greater_than": {
        "label": "Greater than",
        "symbol": ">",
        "example": "EPOCH/>now-10",
    },
    "less_than": {
        "label": "Less than",
        "symbol": "<",
        "example": "PERIGEE/<2000",
    },
    "not_equal": {
        "label": "Not equal",
        "symbol": "<>",
        "example": "DECAY_DATE/<>null-val",
    },
    "range": {
        "label": "Inclusive range",
        "symbol": "--",
        "example": "NORAD_CAT_ID/25544--26000",
    },
    "comma_or": {
        "label": "Comma-delimited OR list",
        "symbol": ",",
        "example": "NORAD_CAT_ID/25544,43013,48274",
    },
    "wildcard_like": {
        "label": "Wildcard like",
        "symbol": "~~",
        "example": "OBJECT_NAME/STARLINK~~",
    },
    "wildcard_after": {
        "label": "Wildcard after value",
        "symbol": "^",
        "example": "OBJECT_NAME/STAR^",
    },
    "null_value": {
        "label": "Null value",
        "symbol": "null-val",
        "example": "DECAY_DATE/null-val",
    },
    "now": {
        "label": "Current time variable",
        "symbol": "now",
        "example": "EPOCH/>now-7",
    },
}


# =============================================================================
# Common predicate descriptions
# =============================================================================

PREDICATE_DESCRIPTIONS: dict[str, str] = {
    "NORAD_CAT_ID": "NORAD catalog identifier",
    "OBJECT_NUMBER": "Object number, commonly equivalent to NORAD catalog ID in some classes",
    "OBJECT_NAME": "Object name",
    "SATNAME": "Satellite name in SATCAT",
    "INTLDES": "International designator",
    "OBJECT_TYPE": "Object type such as PAYLOAD, ROCKET BODY, DEBRIS, or UNKNOWN",
    "COUNTRY": "Country or owner field in SATCAT",
    "COUNTRY_CODE": "Country or owner code in GP-related classes",
    "SITE": "Launch site code",
    "LAUNCH": "Launch date in SATCAT",
    "LAUNCH_DATE": "Launch date in GP-related classes",
    "DECAY": "Decay date in SATCAT",
    "DECAY_DATE": "Decay date in GP-related classes",
    "PERIOD": "Orbital period in minutes",
    "INCLINATION": "Inclination in degrees",
    "INCL": "Inclination in degrees",
    "APOGEE": "Apogee altitude in kilometers",
    "PERIGEE": "Perigee altitude in kilometers",
    "ECCENTRICITY": "Orbital eccentricity",
    "MEAN_MOTION": "Mean motion in revolutions per day",
    "RCS": "Radar cross section value or category",
    "RCS_SIZE": "Radar cross-section size category: SMALL, MEDIUM, or LARGE",
    "EPOCH": "Epoch of the element set",
    "CREATION_DATE": "Date the element set was created or published",
    "FILE": "Space-Track file or batch identifier",
    "GP_ID": "Unique GP ephemeris identifier",
    "CURRENT": "Current SATCAT record indicator",
    "COMMENTCODE": "SATCAT status/comment code",
    "PRECEDENCE": "Decay lifecycle precedence code",
    "MSG_EPOCH": "Message generation epoch",
    "INSERT_EPOCH": "Database insertion epoch",
    "DECAY_EPOCH": "Predicted or historical reentry epoch",
    "WINDOW": "TIP decay window in minutes",
    "LAT": "Latitude",
    "LON": "Longitude",
    "NEXT_REPORT": "Hours until next expected TIP report",
    "HIGH_INTEREST": "High-interest flag",
    "CDM_ID": "Conjunction Data Message identifier",
    "CREATED": "CDM creation timestamp",
    "TCA": "Time of closest approach",
    "MIN_RNG": "Minimum range at closest approach",
    "PC": "Probability of collision",
    "EMERGENCY_REPORTABLE": "Emergency-reportable conjunction flag",
    "SAT_1_ID": "First object ID in a conjunction",
    "SAT_1_NAME": "First object name in a conjunction",
    "SAT1_OBJECT_TYPE": "First object type in a conjunction",
    "SAT1_RCS": "First object RCS category in a conjunction",
    "SAT_2_ID": "Second object ID in a conjunction",
    "SAT_2_NAME": "Second object name in a conjunction",
    "SAT2_OBJECT_TYPE": "Second object type in a conjunction",
    "SAT2_RCS": "Second object RCS category in a conjunction",
    "DEBUT": "Date/time object was first added to SATCAT",
    "CHANGE_DATE": "Date/time of SATCAT change",
    "SITE_CODE": "Launch site code",
    "LAUNCH_SITE": "Launch site name",
    "name": "Public file name or LINK value used by the publicfiles download endpoint",
}


# =============================================================================
# Helper functions
# =============================================================================

def get_dataset(dataset_key: str) -> DatasetConfig:
    """
    Return a dataset configuration by key.

    Raises:
        KeyError:
            If the dataset key is unknown.
    """
    try:
        return DATASETS[dataset_key]
    except KeyError as exc:
        available = ", ".join(sorted(DATASETS))
        raise KeyError(
            f"Unknown dataset key: {dataset_key!r}. "
            f"Available datasets: {available}"
        ) from exc


def list_dataset_keys() -> list[str]:
    """
    Return all dataset keys in insertion order.
    """
    return list(DATASETS.keys())


def list_dataset_group_keys() -> list[str]:
    """
    Return all dataset group keys in insertion order.
    """
    return list(DATASET_GROUPS.keys())


def get_dataset_group(group_key: str) -> dict[str, Any]:
    """
    Return a dataset group by key.

    Raises:
        KeyError:
            If the group key is unknown.
    """
    try:
        return DATASET_GROUPS[group_key]
    except KeyError as exc:
        available = ", ".join(sorted(DATASET_GROUPS))
        raise KeyError(
            f"Unknown dataset group key: {group_key!r}. "
            f"Available groups: {available}"
        ) from exc


def get_supported_formats(dataset_key: str) -> tuple[str, ...]:
    """
    Return supported formats for a dataset.
    """
    return get_dataset(dataset_key).supported_formats


def is_supported_format(dataset_key: str, output_format: str) -> bool:
    """
    Return True if a format is supported by the selected dataset.
    """
    return output_format in get_supported_formats(dataset_key)


def get_default_format(dataset_key: str) -> str:
    """
    Return the default output format for a dataset.
    """
    return get_dataset(dataset_key).default_format


def get_default_orderby(dataset_key: str) -> str | None:
    """
    Return the default orderby value for a dataset.
    """
    return get_dataset(dataset_key).default_orderby


def get_common_filters(dataset_key: str) -> tuple[str, ...]:
    """
    Return common filters for a dataset.
    """
    return get_dataset(dataset_key).common_filters


def get_recommended_filters(dataset_key: str) -> dict[str, str]:
    """
    Return a copy of the recommended filters for a dataset.
    """
    return dict(get_dataset(dataset_key).recommended_filters)


def get_object_type_filter(option_key: str) -> dict[str, str]:
    """
    Return a copy of an object-type preset filter dictionary.
    """
    try:
        return dict(OBJECT_TYPE_FILTERS[option_key]["filters"])
    except KeyError as exc:
        available = ", ".join(sorted(OBJECT_TYPE_FILTERS))
        raise KeyError(
            f"Unknown object-type option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc


def get_orbit_regime_filter(option_key: str) -> dict[str, str]:
    """
    Return a copy of an orbit-regime preset filter dictionary.
    """
    try:
        return dict(ORBIT_REGIME_FILTERS[option_key]["filters"])
    except KeyError as exc:
        available = ", ".join(sorted(ORBIT_REGIME_FILTERS))
        raise KeyError(
            f"Unknown orbit-regime option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc


def get_rcs_size_filter(option_key: str) -> dict[str, str]:
    """
    Return a copy of an RCS-size preset filter dictionary.
    """
    try:
        return dict(RCS_SIZE_FILTERS[option_key]["filters"])
    except KeyError as exc:
        available = ", ".join(sorted(RCS_SIZE_FILTERS))
        raise KeyError(
            f"Unknown RCS-size option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc


def get_epoch_recency_filter(option_key: str) -> dict[str, str]:
    """
    Return a copy of an epoch-recency preset filter dictionary.
    """
    try:
        return dict(EPOCH_RECENCY_FILTERS[option_key]["filters"])
    except KeyError as exc:
        available = ", ".join(sorted(EPOCH_RECENCY_FILTERS))
        raise KeyError(
            f"Unknown epoch-recency option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc


def get_creation_date_recency_filter(option_key: str) -> dict[str, str]:
    """
    Return a copy of a creation-date-recency preset filter dictionary.
    """
    try:
        return dict(CREATION_DATE_RECENCY_FILTERS[option_key]["filters"])
    except KeyError as exc:
        available = ", ".join(sorted(CREATION_DATE_RECENCY_FILTERS))
        raise KeyError(
            f"Unknown creation-date-recency option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc


def get_country_code(option_key: str) -> str | None:
    """
    Return a country code from the country presets.

    Returns:
        None:
            If the selected option represents all countries.

        "custom":
            If the user should be prompted for a custom country code.
    """
    try:
        value = COUNTRY_PRESETS[option_key]["value"]
    except KeyError as exc:
        available = ", ".join(sorted(COUNTRY_PRESETS))
        raise KeyError(
            f"Unknown country option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc

    return value


def get_favorite_value(option_key: str) -> str:
    """
    Return a Space-Track favorites value.
    """
    try:
        return str(FAVORITES_PRESETS[option_key]["value"])
    except KeyError as exc:
        available = ", ".join(sorted(FAVORITES_PRESETS))
        raise KeyError(
            f"Unknown favorites option: {option_key!r}. "
            f"Available options: {available}"
        ) from exc


def get_predicate_description(predicate: str) -> str:
    """
    Return a human-readable predicate description.
    """
    return PREDICATE_DESCRIPTIONS.get(predicate, "No description available")


def merge_filters(*filter_sets: dict[str, str]) -> dict[str, str]:
    """
    Merge multiple filter dictionaries.

    Later dictionaries override earlier dictionaries if the same predicate is
    provided more than once.
    """
    merged: dict[str, str] = {}

    for filter_set in filter_sets:
        merged.update(filter_set)

    return merged


def validate_dataset_format(dataset_key: str, output_format: str) -> None:
    """
    Validate that an output format is supported by a dataset.

    Raises:
        ValueError:
            If the output format is not supported.
    """
    supported = get_supported_formats(dataset_key)

    if output_format not in supported:
        supported_text = ", ".join(supported)
        raise ValueError(
            f"Format {output_format!r} is not supported for dataset "
            f"{dataset_key!r}. Supported formats: {supported_text}"
        )


def should_warn_legacy_tle(dataset_key: str, output_format: str) -> bool:
    """
    Return True if the selected format is a legacy TLE-style format.
    """
    dataset = get_dataset(dataset_key)

    return dataset.allow_tle_formats and output_format in {"tle", "3le"}


def dataset_uses_publicfiles_controller(dataset_key: str) -> bool:
    """
    Return True if the dataset uses the publicfiles controller.
    """
    return get_dataset(dataset_key).is_publicfiles_endpoint


def dataset_supports_metadata(dataset_key: str, output_format: str | None = None) -> bool:
    """
    Return True if metadata/true is meaningful for this dataset and format.

    Space-Track ignores metadata for CSV, TLE, and 3LE formats.
    """
    dataset = get_dataset(dataset_key)

    if not dataset.supports_metadata:
        return False

    if output_format in {"csv", "tle", "3le", "kvn"}:
        return False

    return True


def get_file_extension(output_format: str) -> str:
    """
    Return a recommended file extension for an output format.
    """
    extension_map: dict[str, str] = {
        "json": ".json",
        "csv": ".csv",
        "xml": ".xml",
        "kvn": ".kvn",
        "html": ".html",
        "tle": ".tle",
        "3le": ".tle",
        "raw": ".bin",
    }

    return extension_map.get(output_format.lower(), f".{output_format.lower()}")


def get_safe_dataset_filename_part(dataset_key: str) -> str:
    """
    Return a safe filename component for a dataset.
    """
    return dataset_key.lower().replace(" ", "_").replace("/", "_")


def print_available_datasets() -> None:
    """
    Print all dataset groups and datasets.

    This helper is useful for quick debugging and early CLI development.
    """
    print("\nAvailable Space-Track dataset groups:")

    for group_key, group in DATASET_GROUPS.items():
        print(f"\n[{group_key}] {group['label']}")
        print(f"  {group['description']}")

        for dataset_key in group["datasets"]:
            dataset = DATASETS[dataset_key]
            print(f"  - {dataset.key}: {dataset.label}")


def print_dataset_details(dataset_key: str) -> None:
    """
    Print detailed information about a dataset.

    This helper is useful for quick debugging and early CLI development.
    """
    dataset = get_dataset(dataset_key)

    print(f"\nDataset: {dataset.label}")
    print(f"Key: {dataset.key}")
    print(f"Controller: {dataset.controller}")
    print(f"Class: {dataset.api_class}")
    print(f"Description: {dataset.description}")
    print(f"Default format: {dataset.default_format}")
    print(f"Supported formats: {', '.join(dataset.supported_formats)}")

    if dataset.default_orderby:
        print(f"Default orderby: {dataset.default_orderby}")

    if dataset.common_filters:
        print("\nCommon filters:")
        for predicate in dataset.common_filters:
            print(f"  - {predicate}: {get_predicate_description(predicate)}")

    if dataset.recommended_filters:
        print("\nRecommended filters:")
        for predicate, value in dataset.recommended_filters.items():
            print(f"  - {predicate}: {value}")

    if dataset.notes:
        print("\nNotes:")
        for note in dataset.notes:
            print(f"  - {note}")