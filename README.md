# Space-Track Data Downloader

An interactive Python command-line downloader and query builder for Space-Track.org data.

This project is designed to be a general-purpose Space-Track downloader, not just a debris/TLE downloader. It lets users select Space-Track datasets, configure filters, preview the REST API query URL, download the result, and save both the data file and metadata.

---

## Features

* Interactive command-line interface
* Space-Track login using environment variables or secure password prompt
* Dataset-based workflow
* Supports multiple Space-Track API classes
* Supports common filters and advanced custom predicate/value filters
* Builds official Space-Track REST-style query URLs
* Shows the final query before download
* Saves downloaded data to a `downloads/` folder
* Saves sidecar metadata for each download
* Supports JSON, CSV, XML, KVN, HTML, TLE, and 3LE where available
* Includes public files listing and download support
* Avoids hardcoded one-purpose debris-only logic

---

## Project Structure

```text
Space-Track_Data_Downloader/
│
├── spacetrack_downloader.py        # Main interactive CLI
├── spacetrack_client.py            # Login, session, and HTTP request functions
├── query_builder.py                # Builds Space-Track REST URLs safely
├── dataset_configs.py              # Dataset menus, class mappings, filter presets
├── exporters.py                    # Saves JSON, CSV, TLE, XML, KVN, HTML, raw files
├── metadata.py                     # Saves metadata sidecar files
├── requirements.txt                # Python dependencies
├── README.md                       # Project documentation
├── .gitignore                      # Files/folders ignored by Git
│
└── downloads/                      # Downloaded files and metadata
```

---

## Requirements

* Python 3.10 or newer recommended
* A Space-Track.org account
* Internet connection

Python package dependency:

```text
requests
```

---

## Quick Start

From inside the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python spacetrack_downloader.py
```

---

## Full Setup on Linux / Zorin OS / Ubuntu

### 1. Open the Project Folder

Open the project folder in VSCodium or your terminal.

Example:

```bash
cd Space-Track_Data_Downloader
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
```

### 3. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

After activation, your terminal should show something like:

```text
(.venv)
```

### 4. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 5. Install Dependencies

```bash
pip install -r requirements.txt
```

### 6. Run the Downloader

```bash
python spacetrack_downloader.py
```

---

## VSCodium Setup

If you are using VSCodium:

1. Open the `Space-Track_Data_Downloader` folder.
2. Open the terminal inside VSCodium.
3. Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Select the virtual environment interpreter:

```text
Ctrl + Shift + P
Python: Select Interpreter
Choose .venv/bin/python
```

6. Run the script:

```bash
python spacetrack_downloader.py
```

---

## Space-Track Account

You need a Space-Track.org account.

1. Go to Space-Track.org.
2. Create a free account.
3. Wait for account approval if required.
4. Use your username/email and password with this downloader.

---

## Credentials

The downloader supports two login methods.

---

### Option 1: Environment Variables

Recommended for repeated use.

Linux/macOS/Zorin OS:

```bash
export SPACETRACK_USER="your_email@example.com"
export SPACETRACK_PASS="your_password"
```

Then run:

```bash
python spacetrack_downloader.py
```

Windows PowerShell:

```powershell
$env:SPACETRACK_USER="your_email@example.com"
$env:SPACETRACK_PASS="your_password"
python spacetrack_downloader.py
```

The script also recognizes these alternative variable names:

```text
SPACETRACK_USERNAME
SPACETRACK_PASSWORD
SPACE_TRACK_USER
SPACE_TRACK_PASS
SPACE_TRACK_USERNAME
SPACE_TRACK_PASSWORD
```

---

### Option 2: Interactive Prompt

If environment variables are not set, the script prompts for:

```text
Username / email
Password
```

The password is entered using a hidden prompt.

---

## Running the Script

Run:

```bash
python spacetrack_downloader.py
```

The script will:

1. Show a responsible API-use reminder.
2. Log in to Space-Track.
3. Show the main dataset menu.
4. Ask which dataset you want.
5. Ask for filters.
6. Ask for output format.
7. Show the final query URL.
8. Ask for confirmation.
9. Download the response.
10. Save the output file.
11. Save a metadata JSON file.

---

## Main Menu

The main menu includes:

```text
1. Object / ELSET data
2. Satellite catalog data
3. Decay / Reentry data
4. Conjunction data
5. Summary / reports
6. Public files
7. Advanced custom query builder
8. Check Space-Track session status
9. Quit
```

---

## Supported Dataset Groups

### Object / ELSET Data

Includes:

```text
gp
gp_history
```

Use `gp` for current/latest element sets.

Use `gp_history` for historical element sets. Historical queries should be limited carefully by object ID and date range.

---

### Satellite Catalog Data

Includes:

```text
satcat
satcat_change
satcat_debut
launch_site
```

Use these for catalog metadata, object names, countries, launch dates, decay dates, launch sites, and recent catalog changes.

---

### Decay / Reentry Data

Includes:

```text
decay
tip
```

Use these for decay history, predicted reentry information, and Tracking and Impact Prediction messages.

---

### Conjunction Data

Includes:

```text
cdm_public
```

Use this for publicly available conjunction data messages.

---

### Summary / Reports

Includes:

```text
boxscore
```

Use this for aggregate object counts grouped by country or organization.

---

### Public Files

Includes:

```text
publicfiles_dirs
publicfiles_files
publicfiles_loadpublicdata
publicfiles_download
```

Use these to list and download files from Space-Track public file endpoints.

---

## Supported Output Formats

Supported formats depend on the selected dataset.

Common formats include:

```text
json
csv
xml
kvn
html
tle
3le
raw
```

### JSON

Recommended for programming and structured processing.

### CSV

Recommended for analysis and spreadsheets.

### XML

Useful for OMM-compatible structured output where supported.

### KVN

Key-value notation where supported.

### HTML

Useful for quick human-readable inspection.

### TLE

Legacy two-line element format.

### 3LE

Legacy three-line format including object name.

### RAW

Used mainly for public file downloads.

---

## Important Note About TLE and 3LE

TLE and 3LE are legacy fixed-width formats. They are useful for compatibility with many orbital tools, but they are not ideal for expanded catalog identifiers.

For general future-proof use, prefer:

```text
json
csv
xml
kvn
```

Use TLE or 3LE only when your downstream software specifically needs those formats.

---

## Example: Download All Active Debris in All Orbits as TLE

This example downloads all debris objects that are currently marked as active/on-orbit, across all orbit regimes, in TLE format.

The final query should include:

```text
OBJECT_TYPE = DEBRIS
DECAY_DATE = null-val
format = tle
```

It should not include:

```text
EPOCH = >now-10
```

because that would limit the result to only debris with recent TLE epochs.

---

### Step-by-Step Menu Choices

Run the downloader:

```bash
python spacetrack_downloader.py
```

When prompted:

```text
Continue? [Y/n]:
```

Press:

```text
Enter
```

At the main menu, choose:

```text
1. Object / ELSET data
```

At the dataset menu, choose:

```text
1. Latest ELSET / GP data
```

At the object type menu, choose:

```text
5. Debris currently in orbit
```

Then answer the prompts as follows:

```text
Configure orbit-regime filter? [Y/n]: n
Configure RCS-size filter? [y/N]: Enter
Configure EPOCH recency filter? [Y/n]: y
EPOCH recency filter: 1. All epochs
Configure CREATION_DATE recency filter? [y/N]: Enter
Country / owner filter: 1. All countries / owners
Filter by NORAD catalog ID, comma list, or range? [y/N]: Enter
Filter by OBJECT_NAME wildcard/name? [y/N]: Enter
Filter by launch site SITE? [y/N]: Enter
Filter by LAUNCH_DATE? [y/N]: Enter
Add advanced custom predicate/value filters? [y/N]: Enter
Filter by Space-Track favorites list? [y/N]: Enter
Output format: 6. TLE
Use default ordering (NORAD_CAT_ID)? [Y/n]: Enter
Apply a result limit? [y/N]: Enter
Show explicit message for empty result? [Y/n]: Enter
Request distinct rows only? [y/N]: Enter
```

Before downloading, confirm that the query summary shows exactly these filters:

```text
Filters:
  - OBJECT_TYPE: DEBRIS
  - DECAY_DATE: null-val
```

The URL should look similar to:

```text
https://www.space-track.org/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS/DECAY_DATE/null-val/orderby/NORAD_CAT_ID/emptyresult/show/format/tle
```

Then proceed:

```text
Proceed with download? [Y/n]: y
```

Use the default output folder:

```text
Download directory [downloads]: Enter
```

You may choose whether to use a custom filename. If not, the script creates a filename like:

```text
downloads/spacetrack_gp_YYYYMMDD_HHMMSS.tle
```

A metadata file is also created:

```text
downloads/spacetrack_gp_YYYYMMDD_HHMMSS_meta.json
```

---

## Example: Download Active Debris with Recent TLEs Only

If you want only debris with recent TLE epochs, use the EPOCH filter.

The final query should include:

```text
OBJECT_TYPE = DEBRIS
DECAY_DATE = null-val
EPOCH = >now-10
format = tle
```

This is useful for orbit propagation because it avoids older element sets.

Menu choices are mostly the same as the previous example, except choose:

```text
Configure EPOCH recency filter? [Y/n]: y
EPOCH recency filter: 4. Last 10 days
```

The query should look similar to:

```text
https://www.space-track.org/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS/DECAY_DATE/null-val/EPOCH/%3Enow-10/orderby/NORAD_CAT_ID/emptyresult/show/format/tle
```

---

## Example: Download Latest Debris GP Data as JSON

Run:

```bash
python spacetrack_downloader.py
```

Then choose:

```text
Object / ELSET data
Latest ELSET / GP data
Object type / object population: Debris currently in orbit
Orbit regime: All orbit regimes
EPOCH recency: Last 10 days
Output format: JSON
```

The script builds a query similar to:

```text
/basicspacedata/query/class/gp/OBJECT_TYPE/DEBRIS/DECAY_DATE/null-val/EPOCH/%3Enow-10/orderby/NORAD_CAT_ID/emptyresult/show/format/json
```

---

## Example: Download Active Payloads in TLE Format

Choose:

```text
Object / ELSET data
Latest ELSET / GP data
Object type / object population: Active payloads
Output format: TLE
```

The script builds a query using the `gp` class and `format/tle`.

---

## Example: Download SATCAT Metadata as CSV

Choose:

```text
Satellite catalog data
Satellite Catalog / SATCAT
Use only current SATCAT records: Yes
Output format: CSV
```

The output will be saved as a `.csv` file.

---

## Example: Download Public Conjunction Data

Choose:

```text
Conjunction data
Public conjunction data / CDM
Filter by CREATED date: Yes
CREATED value: >now-1
Output format: JSON
```

---

## Example: List Public Files

Choose:

```text
Public files
Public files - detailed file metadata
```

This returns detailed file information including source, type, date, link, name, and size.

---

## Example: Download a Public File

First use:

```text
Public files - detailed file metadata
```

Copy the `LINK` value from the returned data.

Then choose:

```text
Public files
Public files - download selected file
```

Paste the `LINK` value when prompted.

---

## Advanced Custom Query Builder

The advanced query builder lets you choose any configured Space-Track dataset and manually add predicate/value filters.

Example custom filters:

```text
Predicate: NORAD_CAT_ID
Value: 25544

Predicate: EPOCH
Value: >now-30

Predicate: OBJECT_NAME
Value: STARLINK~~

Predicate: PERIOD
Value: 1430--1450

Predicate: DECAY_DATE
Value: null-val
```

---

## Space-Track REST Operators

The downloader supports normal Space-Track REST values such as:

```text
>             greater than
<             less than
<>            not equal
,             comma-delimited OR list
--            inclusive range
null-val      null value
~~            wildcard-like search
^             wildcard-after search
now           current time variable
```

Examples:

```text
EPOCH/>now-10
PERIGEE/<2000
NORAD_CAT_ID/25544,43013,48274
NORAD_CAT_ID/25544--26000
OBJECT_NAME/STARLINK~~
DECAY_DATE/null-val
DECAY_DATE/<>null-val
```

---

## Output Files

Downloaded files are saved to the `downloads/` folder by default.

Example:

```text
downloads/spacetrack_gp_20260528_113000.json
```

A metadata sidecar file is also saved:

```text
downloads/spacetrack_gp_20260528_113000_meta.json
```

---

## Metadata Files

Each metadata file includes:

```text
source
created_utc
dataset_key
dataset_label
controller
api_class
output_format
query_url
relative_query_path
filters
predicates
orderby
limit
offset
favorites
metadata_requested
metadata_supported
show_empty
distinct
output_file
output_filename
output_size_bytes
estimated_record_count
response_status_code
response_elapsed_seconds
response_headers
runtime information
notes
```

This makes it easier to reproduce, audit, and debug downloads later.

---

## Responsible API Use

Space-Track.org throttles API usage to preserve performance for all users.

Best practices:

* Avoid hundreds of small per-object API queries.
* Prefer one efficient query with filters.
* Use comma-delimited lists for multiple object IDs.
* Use date windows such as `>now-1`, `>now-7`, or `>now-10`.
* Save downloaded data locally instead of repeatedly downloading the same records.
* Avoid running large downloads repeatedly.
* For current ephemerides, use `gp`.
* For historical ephemerides, use `gp_history` carefully with object IDs and short date ranges.

---

## Git Ignore Recommendations

The project should include a `.gitignore` file.

Recommended ignored files/folders include:

```text
.venv/
__pycache__/
downloads/
.env
.env.*
*.tle
*_meta.json
.spacetrack_cache/
```

Do not commit:

* Space-Track credentials
* downloaded data files
* metadata containing query history
* virtual environments
* Python cache files

---

## Current Design Philosophy

This project intentionally separates responsibilities.

### `dataset_configs.py`

Defines what datasets exist, their Space-Track classes, supported formats, common predicates, filter presets, and menu groupings.

### `query_builder.py`

Builds safe REST query URLs. It handles encoding values such as `>now-10`, `<2000`, comma lists, ranges, and wildcard values.

### `spacetrack_client.py`

Handles authentication, sessions, requests, retries, `whoami`, logout, and downloads.

### `exporters.py`

Saves Space-Track responses to disk, estimates record counts, and prints previews.

### `metadata.py`

Creates and saves metadata sidecar files.

### `spacetrack_downloader.py`

Provides the interactive user interface and connects all other modules together.

---


## Troubleshooting

### Login Failed

Check:

* Username/email is correct.
* Password is correct.
* Space-Track account is approved.
* Environment variables are set correctly.
* You are using the official Space-Track account credentials.

---

### HTTP 401 Unauthorized

Your session may have expired or credentials may be invalid.

Try running the script again and logging in again.

---

### HTTP 403 Forbidden

Your account may not have access to that dataset or endpoint.

---

### No Results Returned

Your filters may be too strict.

Try:

* Removing object type filters.
* Removing orbit filters.
* Increasing the EPOCH range.
* Using JSON instead of TLE/3LE.
* Removing country filters.
* Using `emptyresult/show` to verify Space-Track returned no results.

---

### TLE or 3LE Missing Objects

Some catalog ranges may not be available in legacy TLE/3LE format.

Try using:

```text
json
csv
xml
kvn
```

instead.

---

### CSV Metadata Missing

Space-Track does not return metadata with CSV in the same way as JSON/XML formats.

This is expected.

---

### Query Is Too Large or Slow

Try:

* Adding `NORAD_CAT_ID`.
* Adding a short `EPOCH` or `CREATION_DATE` range.
* Adding `limit`.
* Using more specific object filters.
* Avoiding broad `gp_history` queries.

---

## Common Commands

Create virtual environment:

```bash
python3 -m venv .venv
```

Activate virtual environment:

```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run script:

```bash
python spacetrack_downloader.py
```

Deactivate virtual environment:

```bash
deactivate
```

---

## Example Environment Setup

Linux/macOS/Zorin OS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

export SPACETRACK_USER="your_email@example.com"
export SPACETRACK_PASS="your_password"

python spacetrack_downloader.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

$env:SPACETRACK_USER="your_email@example.com"
$env:SPACETRACK_PASS="your_password"

python spacetrack_downloader.py
```

---

## Security Notes

* Do not hardcode your Space-Track password in source code.
* Do not commit credentials to Git.
* Prefer environment variables for repeated use.
* Keep downloaded data and metadata organized.
* Be careful before sharing metadata files, because they may reveal query patterns or downloaded file names.

---

## License

This project is licensed under the MIT License.

Copyright (c) 2026 Sooraj Suresh

See the [LICENSE](LICENSE) file for details.

---

## Status

Initial general downloader version.

The project currently supports an interactive workflow and modular code organization. More advanced features such as model-definition caching, saved profiles, and non-interactive batch mode can be added later.
