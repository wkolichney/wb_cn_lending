# World Bank Projects & Documents Database (`wb_proj_doc`)

**Author:** William Olichney · **Started:** April 2026

A MySQL database that pulls **World Bank project and project-document data** and attaches
a panel of **country-year control variables**, built to compare Chinese development
finance with World Bank development finance. The end product is a project-level
regression table exported to Excel.

- **32 tables** — a World Bank project/document core plus 11 country-year control datasets.
- **~27,900 projects** and **~365,000 documents** (2000–2025).
- One reproducible pipeline: create schema → run loaders → export.

---

## Contents

1. [Repository layout](#repository-layout)
2. [Quick start (from a fresh MySQL install)](#quick-start-from-a-fresh-mysql-install)
3. [Database schema & how the joins work](#database-schema--how-the-joins-work)
4. [Data sources](#data-sources)
5. [Data availability](#data-availability)
6. [Build pipeline (detailed order)](#build-pipeline-detailed-order)
7. [The country-name crosswalk](#the-country-name-crosswalk)
8. [Regression export](#regression-export)

---

## Repository layout

| Path | Contents |
|------|----------|
| `sql_queries/` | Schema DDL (`proj_doc.sql` + one file per control table), plus `data_availability.sql` and ad-hoc analysis queries. |
| `sql_insert_scripts/` | Python loaders that populate the tables (World Bank / IMF / OECD APIs + the raw files in `manual_file_location/`). |
| `manual_file_location/` | Raw source files that must be downloaded by hand. Git-ignored — see its `README.md` for sources. |
| `codebook/` | Published reference artifacts, incl. the `country_alternate.csv` name crosswalk. |
| `sql_export/` | `main_regression_export.py` (joins everything into one Excel table) and `make_erd.py` (regenerates the ERD). |
| `images/` | `erd_schema.png` — the entity-relationship diagram below. |
| `fdi_analysis/` | Standalone comparison of alternative China-FDI sources. |
| `archive/` | Exploratory notebooks and the one-time crosswalk-construction scripts (git-ignored). |

---

## Quick start (from a fresh MySQL install)

**0. Install MySQL Server** (8.x recommended) and make sure the `mysql` client is on your
`PATH`. Download: <https://dev.mysql.com/downloads/mysql/>. Start the server.

> **Connection string.** Every Python script connects with
> `mysql+pymysql://root:root@localhost/wb_proj_doc` (user `root`, password `root`).
> If your MySQL uses different credentials, either create a matching `root`/`root` local
> user or find-and-replace that string across `sql_insert_scripts/*.py` and `sql_export/`.

**1. Clone and enter the repo**
```bash
git clone https://github.com/wkolichney/wb_cn_lending
cd wb_cn_lending
```

**2. Install Python dependencies**
```bash
pip install -r requirements.txt
```

**3. Download the raw data.** Put the files listed in
[`manual_file_location/README.md`](manual_file_location/README.md) into that folder using
the exact filenames given. (Everything else is pulled live from APIs by the scripts.)

**4. Build the database** — create the schema, run the loaders, export. See
[Build pipeline](#build-pipeline-detailed-order) for the full ordered command list. The
short version:
```bash
cd sql_queries && mysql -u root -p wb_proj_doc < proj_doc.sql   # + the other .sql files
cd ../sql_insert_scripts && python insert_project.py            # then the rest, in order
cd ../sql_export && python main_regression_export.py            # -> project_document_regression.xlsx
```

**5. Sanity-check coverage** at any point:
```bash
mysql -u root -p wb_proj_doc < sql_queries/data_availability.sql
```

---

## Database schema & how the joins work

![Entity-relationship diagram](images/erd_schema.png)

*(Regenerate with `python sql_export/make_erd.py`. Arrows point child → parent.)*

The schema has **one hub table, `country`**, and everything hangs off it. The key thing
to understand is that there are **two country keys**, because the World Bank project API
does not use ISO codes:

| Key | Used by | Meaning |
|-----|---------|---------|
| `countryshortname` | the WB **project/document** side (`projects`, `doc_country`) | the World Bank's own country name (the PK of `country`) |
| `iso3` | every **country-year control** table | ISO 3166-1 alpha-3 code |

`country` carries **both**, so it bridges the two halves of the database.

### The four join families

**1. Project ↔ country (by name).** Projects join to `country` on `countryshortname`:
```sql
SELECT p.project_id, p.project_name, c.iso3
FROM projects p
JOIN country c ON c.countryshortname = p.countryshortname;
```

**2. Project → documents → document detail.** Documents belong to a project; each
document's themes/sectors/countries live in child tables that also point at lookups:
```sql
SELECT p.project_name, d.document_type, d.docdt
FROM projects p
JOIN documents d ON d.project_id = p.project_id
WHERE d.document_type = 'Project Appraisal Document';
```
`documents` → `doc_theme` / `doc_sector` / `doc_sub_sector` / `doc_country`
(each validated against its `*_lookup` table), and `doc_country` → `country`.

**3. Project → sector chain → infrastructure flag.** A project's sector percentages roll
up to a "major sector," which maps to a condensed sector carrying an `infrastructure`
flag:
```sql
SELECT p.project_id, ms.major_sector_name, ps.sector_percent, wcs.infrastructure
FROM projects p
JOIN project_sectors        ps  ON ps.project_id = p.project_id
JOIN project_major_sectors  pms ON pms.project_major_sector_id = ps.project_major_sector_id
JOIN major_sector_lookup    ms  ON ms.major_sector_code = pms.major_sector_code
JOIN wb_condensed_sector    wcs ON wcs.wb_condensed_sector_name = ms.wb_condensed_sector_name;
```

**4. Country-year controls (by iso3 + year).** Every control table
(`corruption`, `democracy`, `dsa_credit`, `oil_gas`, `trade_china`, `un_cn_agree`,
`taiwan_recognition`, `bilateral_fdi`, `dac_oda`, `ucdp_conflict`, `wb_indicator_pull`)
is keyed on `(iso3, year)`. Attach one to a project at its board-approval year:
```sql
SELECT p.project_id, c.iso3, YEAR(p.boardapprovaldate) AS yr, corr.v2x_pubcorr
FROM projects p
JOIN country c        ON c.countryshortname = p.countryshortname
LEFT JOIN corruption corr ON corr.iso3 = c.iso3
                         AND corr.year = YEAR(p.boardapprovaldate);
```
`china_steel` is the one exception: it is a **global** yearly series (no country), so it
joins on `year` alone. `main_regression_export.py` performs exactly these joins to build
the analysis table.

> When a source spells a country differently from the WB's canonical name, resolve it
> through the **`country_alternate`** crosswalk (see below) instead of joining on the raw
> name.

---

## Data sources

Fill in the URL column with the canonical download/citation link for each source.

| Dataset | Loaded into | Access | Source / citation | URL |
|---------|-------------|--------|-------------------|-----|
| World Bank Projects & Operations | `projects`, `borrower`, `impagency`, sector tables | API | World Bank Projects API | _https://search.worldbank.org/api/v3/projects_ |
| World Bank Documents & Reports | `documents`, `doc_*` | API | World Bank D&R API | _https://search.worldbank.org/api/v3/wds_ |
| WB World Development Indicators | `wb_indicator_pull`, `wb_indicators` | API (`bblocks`) | World Bank WDI | _https://databank.worldbank.org/source/world-development-indicators_ |
| WB Worldwide Governance Indicators | `wb_indicator_pull` | API (`wbgapi`) | World Bank WGI | _https://www.worldbank.org/en/publication/worldwide-governance-indicators_ |
| OECD DAC2A ODA disbursements | `dac_oda` | API (SDMX) | OECD DAC2A | _https://data-explorer.oecd.org/vis?df[ds]=DisseminateFinalDMZ&df[id]=DSD_DAC2%40DF_DAC2A&df[ag]=OECD.DCD.FSD&dq=.ALLR.206.USD.Q&lom=LASTNPERIODS&lo=5&to[TIME_PERIOD]=false_ |
| China steel production | `china_steel` | API | chinadata.live | _https://chinadata.live/api/v2/data/steel-production-china-vs-world_ |
| IMF Coordinated Direct Investment Survey | `bilateral_fdi` | manual | IMF CDIS | _https://data360.worldbank.org/en/dataset/IMF_CDIS_ |
| IMF Int'l Merchandise Trade Statistics | `trade_china` | manual | IMF IMTS | _https://data.imf.org/en/datasets/IMF.STA:IMTS_ |
| IMF Debt Sustainability Analysis + ratings | `dsa_credit`, `credit_lookup` | manual | IMF DSA; S&P/Moody's/Fitch - Economist Intelligent Unit |
| Polity5 | `democracy` | manual | Center for Systemic Peace | _https://www.systemicpeace.org/polityproject.html_ |
| V-Dem (Country-Year Core v16) | `corruption` | manual | V-Dem Institute | _https://www.v-dem.net/data/the-v-dem-dataset/_ |
| UCDP/PRIO Armed Conflict Dataset v26.1 | `ucdp_conflict` | manual | UCDP / PRIO | _https://ucdp.uu.se/downloads/#armedconflict_ |
| UN GA voting / ideal points | `un_cn_agree` | manual | Bailey/Strezhnev/Voeten (Dataverse doi:10.7910/DVN/LEJUQZ) | _https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/LEJUQZ_ |
| Diplomatic recognition (Taiwan) | `taiwan_recognition` | manual | ICPSR study 30802 | _https://www.icpsr.umich.edu/web/ICPSR/studies/30802#_ |
| Ross–Mahdavi Oil & Gas 1932–2014 | `oil_gas` | manual | Ross & Mahdavi | _https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/ZTPW0Y_ |

See [`manual_file_location/README.md`](manual_file_location/README.md) for the exact file
name, version, and consuming script of each **manual** source.

---

## Data availability

Coverage as of the current build (regenerate with
[`sql_queries/data_availability.sql`](sql_queries/data_availability.sql)). `% countries`
is relative to the **189** countries in `country` that carry an `iso3`.

**World Bank core**

| Table | Rows | Coverage | Span |
|-------|-----:|----------|------|
| `projects` | 27,872 | 216 countries/regions | approval 1947–2027 |
| `documents` | 364,863 | 14,837 projects | docdt 2000–2025 |
| `country` | 216 | 189 with iso3 | — |

**Country-year controls** (keyed on `iso3` + `year`)

| Table | Rows | Countries | % countries | Year span |
|-------|-----:|----------:|:-----------:|-----------|
| `wb_indicator_pull` | 45,213 | 179 | 95% | 2000–2024 |
| `trade_china` | 4,355 | 177 | 94% | 2000–2024 |
| `un_cn_agree` | 18,524 | 173 | 92% | 1946–2024 |
| `taiwan_recognition` | 14,928 | 171 | 90% | 1950–2007 |
| `dsa_credit` | 1,461 | 164 | 87% | 2007–2026 |
| `corruption` | 23,087 | 162 | 86% | 1789–2025 |
| `oil_gas` | 13,031 | 156 | 83% | 1932–2014 |
| `democracy` | 14,689 | 154 | 81% | 1800–2018 |
| `dac_oda` | 14,301 | 146 | 77% | 2000–2024 |
| `bilateral_fdi` | 1,420 | 110 | 58% | 2009–2023 |
| `ucdp_conflict` | 2,756 | 109 | 58% | 1946–2025 |

**Global series:** `china_steel` — 36 rows, 1990–2025 (no country dimension).

> Several sources extend far outside the analysis window (e.g. `corruption` back to 1789,
> `democracy` to 1800). The regression export filters to `boardapprovaldate > 2000` and
> joins each control at the project's approval year, so only ~2000-onward country-years
> are actually used. `ucdp_conflict` records only *active* conflict-years, so a
> non-match there means "no conflict" (coded 0), not missing.

---

## Build pipeline (detailed order)

Run from the repository root.

### 1. Create the schema
`proj_doc.sql` creates the `wb_proj_doc` database and the core project/document tables;
the remaining files add one control table each.
```bash
cd sql_queries
mysql -u root -p wb_proj_doc < proj_doc.sql
for f in china_steel cn_agree conflict corruption country_alternate dac_oda \
         democracy dsa_credit fdi insert_trade_china oil_gas taiwan wb_indicator; do
    mysql -u root -p wb_proj_doc < "$f.sql"
done
cd ..
```

### 2. Core load (order matters — foreign keys)
```bash
cd sql_insert_scripts
python insert_project.py            # projects, sectors, and country (names only)
python insert_iso3_country.py       # fill country.iso3   (World Bank API)
python insert_iso2.py               # fill country.iso2   (GCI country table)
python insert_country_alternate.py  # load the name crosswalk from codebook/
python insert_wb_sector_manual_id.py# map API sectors -> condensed sectors + infra flag
python insert_document.py           # project documents (World Bank API)
```
`insert_country_alternate.py` must run before any name-keyed control loader, since those
resolve country names through `country_alternate`.

### 3. Country-year control variables
```bash
python insert_wb_indicator.py       # WB development indicators (API)
python insert_wgi.py                # WB governance indicators (API)
python insert_china_steel.py        # China steel production (API)
python insert_un_voting.py          # UN voting agreement / ideal points
python insert_taiwan_approval.py    # Taiwan diplomatic recognition
python insert_dsa_credit.py         # IMF DSA + sovereign credit ratings
python insert_democracy.py          # Polity5
python insert_corruption.py         # V-Dem public-sector corruption
python insert_conflict.py           # UCDP/PRIO armed conflict
python fdi_imf.py                   # China bilateral FDI (IMF CDIS)
python insert_dac_oda.py            # OECD DAC2A ODA disbursements (API)
python insert_oil_gas.py            # Ross-Mahdavi oil & gas production/value
python insert_trade_china.py        # exports to China + export share of GDP
```
> **Ordering note:** `insert_trade_china.py` joins GDP from `wb_indicator_pull`, so run
> `insert_wb_indicator.py` before it.

---

## The country-name crosswalk

Every external source spells country names differently. They are reconciled to a single
ISO-3 code by a crosswalk that maps **each observed spelling → one iso3**. The resolved
crosswalk is published at [`codebook/country_alternate.csv`](codebook/country_alternate.csv)
(253 spellings; 188 countries plus 7 no-code regions) and documented in
[`codebook/README.md`](codebook/README.md).

That CSV is the **single source of truth**: `insert_country_alternate.py` loads it
verbatim. To add a spelling for a new source, add a row to the CSV and re-run the loader.
The original hand-reconciliation scripts are preserved under `archive/drafting/validation/`.

**Maintenance:** when a new UCDP vintage introduces location names that don't resolve,
`insert_conflict.py` writes them to `unmatched_locations.csv`; fill in the `iso3` column,
add the rows to `codebook/country_alternate.csv`, and re-run `insert_country_alternate.py`.

---

## Regression export

```bash
cd sql_export
python main_regression_export.py     # -> project_document_regression.xlsx
```
This performs the joins in [How the joins work](#database-schema--how-the-joins-work):
one row per project × major-sector, with document first/last dates per type and every
country-year control attached at the project's board-approval year.
