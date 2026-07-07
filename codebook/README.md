# Codebook

Public, citable reference artifacts for the World Bank / China lending database.

## `country_alternate.csv` — country-name crosswalk

External data sources (World Bank project API, IMF DSA & CDIS, OECD DAC, Polity5,
V-Dem, UCDP/PRIO, the Taiwan diplomatic-recognition dataset, ...) each spell country
names differently. To join them onto a single country key we maintain a crosswalk
that maps **every observed spelling → one ISO 3166-1 alpha-3 code**. This file is that
crosswalk, frozen from the project database.

| column             | description                                                                 |
|--------------------|-----------------------------------------------------------------------------|
| `iso3`             | ISO 3166-1 alpha-3 code. **Blank** for in-scope aggregate regions that have no country code (see below). |
| `iso2`             | ISO 3166-1 alpha-2 code (blank where not applicable, e.g. regions).         |
| `countryshortname` | An observed spelling of the country/region. Each spelling appears once and resolves to exactly one `iso3`. |

### Row semantics

- **246 rows** carry an `iso3` and cover **188 distinct countries** — the same country
  can appear on several rows, one per alternate spelling.
- **7 rows** have a blank `iso3`: World-Bank aggregate regions that are in scope but have
  no country code (e.g. *Africa*, *Central America*, *Europe and Central Asia*). They
  resolve on name only.

### How it was built

The crosswalk was assembled by hand-reconciling the country-name columns of each source
(World Bank, IMF DSA, OECD DAC, Polity5, V-Dem, UCDP/PRIO, Taiwan recognition, ...)
against the World Bank project API's canonical `countryshortname`. Historical or
non-borrower entities that never appear in the project data (e.g. USSR, Yugoslavia,
Prussia, the United States), and source-side aggregates (e.g. DAC "… unspecified" /
income-group / multilateral rows), are intentionally left unmapped and dropped
downstream. The one-time construction scripts are preserved for provenance under
`archive/drafting/` (they are not part of the reproducible load pipeline).

### How it is used / reproduced

`sql_insert_scripts/insert_country_alternate.py` loads this CSV verbatim into the
`country_alternate` table (a clean, idempotent reload). This file is therefore the
**single source of truth**: to add a spelling for a new source, add a row here and re-run
that loader. Every other source-insert script resolves its country names by joining on
`country_alternate.countryshortname`.

### Citation

If you use this crosswalk, please cite the database and note the constituent sources
listed in `manual_file_location/README.md`.
