# CLAUDE.md

- Always use the Python interpreter in .venv

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Interactive CLI for downloading data from the space-track.org REST API (GP/ELSET, SATCAT, decay/TIP, public CDM, boxscore, public files). Python 3.10+, sole dependency `requests`. Flat layout: six top-level modules, no package, no build step.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python spacetrack_downloader.py          # run the interactive app (needs a Space-Track account)
```

Tests (pytest, fully offline; no linter config or CI):

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest                                       # whole suite
.venv/bin/python -m pytest tests/test_query_builder.py           # one module
.venv/bin/python -m pytest "tests/test_exporters.py::test_count_csv_records"   # one test
.venv/bin/python -m pytest --runxfail                             # show why known-bug tests fail
```

- `.venv` was created with Python 3.12 but `.venv/bin/python` resolves to the system `python3`; inside the VSCodium Flatpak sandbox that is 3.13, whose packages live in `.venv/lib/python3.13` alongside the 3.12 ones.
- `tests/conftest.py` autouse fixtures block real HTTP (`HTTPAdapter.send` raises), `chdir` into `tmp_path` (exporters default to a CWD-relative `downloads/`), clear `SPACETRACK_*` env vars, and record retry sleeps. Fake the client with `make_client([FakeResponse(...), ...])`; drive prompts with `scripted_input.set(...)` (fails if answers are left over) or `scripted_input.enter_for_all()`.
- `spacetrack_downloader` uses `from X import name`, so monkeypatch names on `spacetrack_downloader`, not the source module.
- `xfail_strict = true`: known bugs are `@pytest.mark.xfail(reason="BUG: ...")`. Fixing one makes its test XPASS → fail; remove the marker then.

Each library module also has a `_self_test()` run via `__main__`:

```bash
python query_builder.py       # offline: prints sample URLs
python exporters.py           # offline: writes downloads/exporter_self_test.json
python metadata.py            # offline: writes a sample output + _meta.json sidecar under downloads/
python spacetrack_client.py   # ONLINE: real login + whoami, needs credentials
```

Credentials come from env vars (`SPACETRACK_USER`/`SPACETRACK_PASS`, aliases `SPACETRACK_USERNAME`, `SPACETRACK_PASSWORD`, `SPACE_TRACK_USER[NAME]`, `SPACE_TRACK_PASS[WORD]`), else a `getpass` prompt.

## Architecture

Dependency direction is strictly downward; only `spacetrack_downloader.py` does user interaction:

```
spacetrack_downloader.py  (prompts, menus, per-dataset filter wizards, orchestration)
  ├─ query_builder.py      → dataset_configs.py
  ├─ spacetrack_client.py  (independent; only depends on requests)
  ├─ exporters.py          → dataset_configs.py
  └─ metadata.py           → dataset_configs.py, exporters.ExportResult
```

- **`dataset_configs.py` is the single source of truth.** `DATASETS: dict[str, DatasetConfig]` defines each dataset's `controller` (`basicspacedata` vs `publicfiles`), `api_class`, supported/default formats, `default_orderby`, and filter hints. Preset filter tables (`OBJECT_TYPE_FILTERS`, orbit regime, RCS size, recency, countries, favorites) live here too. Adding a dataset starts here.
- **Adding a dataset also requires routing in the downloader**: `configure_dataset_filters()` dispatches on hardcoded dataset keys (`gp`/`gp_history`, satcat family, `decay`/`tip`, `cdm_public`, `boxscore`, publicfiles); anything else falls to `configure_generic_dataset`.
- **Download pipeline** lives in `execute_download_flow()`:
  1. `build_query_url()` + `summarize_query()` with identical args (keep them in sync — the summary feeds metadata).
  2. `client.get(url, timeout_seconds=client.download_timeout_seconds)`.
  3. Export via `export_public_file_bytes` for `publicfiles_download` (keeps the original file name; checked first because that dataset is always `raw`), else `export_binary_response` (`raw`) or `export_response` (text).
  4. `save_metadata_for_export()` writes `<output_stem>_meta.json`; failure here is non-fatal.
  Errors at each stage print a warning and return to the menu rather than exiting.
- **URL construction** (`build_basicspacedata_url`) appends segments in a fixed order: filters → favorites → predicates → orderby → limit → distinct → metadata → emptyresult → format. Values are encoded with `quote(safe=",-.~")` so Space-Track operators (`,` OR-list, `--` range, `~~` wildcard, `null-val`) survive while `>`, `<`, spaces are escaped. `/metadata/true` is silently dropped for formats Space-Track ignores it on (csv/tle/3le/kvn); `raw` emits no `/format/` segment.
- **`SpaceTrackClient`** wraps a cookie-authenticated `requests.Session` (login = POST `/ajaxauth/login`). `request()` refuses anything but `https` on space-track.org or a subdomain (`is_space_track_url` compares `hostname`, so ports are fine and look-alikes fail), raises immediately on 401/403, and retries timeouts/connection errors and 408/409/425/429/5xx with linear backoff (`retry_delay_seconds * attempt`).
- **Exporters** default to `downloads/spacetrack_{dataset}_{UTC timestamp}{ext}` and append `_1`, `_2`… instead of overwriting unless `overwrite=True`. Record counts are format-specific heuristics and may be `None`.

## Conventions and gotchas

- Every source file begins with the same ASCII-art banner header block (PROJECT NAME / FILE / PATH / AUTHOR / DATE / VERSION / DESCRIPTION); keep it on new files.
- Style: `from __future__ import annotations`, dataclasses for data containers (`DatasetConfig`, `ExportResult` are frozen), per-module exception hierarchies (`QueryBuilderError`, `SpaceTrackClientError`, `ExporterError`, `MetadataError`), section dividers `# ===...`.
- TLE/3LE are treated as legacy formats (warned about in the UI and in metadata notes); prefer JSON/CSV/XML/KVN.
- Metadata sidecars store the response headers minus `Set-Cookie`/`Cookie` (`metadata.SENSITIVE_HEADER_NAMES`, stripped by `sanitize_response_headers`). `downloads/` and `*_meta.json` are gitignored; don't move outputs outside them.
- `.gitignore` also ignores `*.json`, `*.csv`, `*.xml`, `*.html`, `*.tle`, `*.kvn` repo-wide (except `example*.json` / `sample*.json`). A trailing `!tests/fixtures/**` rule re-includes test fixtures, so put fixture data there.
- Respect Space-Track rate limits: favor one filtered query over many per-object queries; `gp_history` should always be narrowed by NORAD ID and a short date window.
