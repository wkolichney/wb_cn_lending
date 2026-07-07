# IMF CDIS (Direct Investment Positions) — China bilateral pulls

Pulled 2026-06-30 for use as a **Chinese-FDI-to-country control variable**.
Reproduce with `python pull_cdis.py`.

## What this is
IMF **CDIS** = "Coordinated Direct Investment Survey", now published as
**Direct Investment Positions by Counterpart Economy (DIP)**, dataset `IMF.STA:DIP`.

- **Annual position (stock) data, in USD millions** — NOT flows.
- Coverage starts **2009**.
- Bilateral: reporter economy × counterpart economy.

Two directions are pulled for each source, because they have very different coverage:

| Direction | Meaning | Use |
|---|---|---|
| **outward (CN→X)** | position China reports it holds in country X | China self-reported |
| **mirror (X←CN)** | position country X reports it received *from* China | usually **more complete** — see below |

**China only began reporting to CDIS in 2018**, so the China-reported *outward* series
only spans 2018–2023. The **mirror** series (host countries reporting inward-from-China)
spans **2009–2023** and covers more years — prefer it, or coalesce mirror ← outward.

## Files

| File | Source | Direction | Rows | Partners | Years |
|---|---|---|---|---|---|
| `cdis_dbnomics_cn_outward.csv` | DBnomics | CN→X | 1545 | 258 | 2018–2023 |
| `cdis_dbnomics_mirror_inward_from_cn.csv` | DBnomics | X←CN | 1574 | 127 | 2009–2023 |
| `cdis_data360_cn_outward.csv` | WB Data360 | CN→X | 1545 | 258 (201 decoded) | 2018–2023 |
| `cdis_data360_mirror_inward_from_cn.csv` | WB Data360 | X←CN | 1423 | 116 | 2009–2023 |
| `cdis_coverage_comparison.csv` | — | summary of the above | | | |

"Partners" counts distinct counterpart economies (outward) or reporting economies (mirror).
The counterpart lists include **aggregate regions** (e.g. "World", "Eastern Asia") alongside
individual countries — filter these out before using as a country-level control.

## Which source to use
**Use DBnomics.** The two sources carry the **identical IMF data** — cross-checking the
outward series on matched (counterpart, year) cells gives **corr = 1.0, max abs diff ≈ 4
USD million** (rounding). But:
- DBnomics is **self-describing** (ISO2 `counterpart_area` + readable `counterpart_label`).
- Data360 stores the counterpart as an **opaque `IMF_CNT_COUNTRY_n` code** (ISO3 reporter,
  raw-USD values ÷ 1e6, direction in `COMP_BREAKDOWN_2`). We decode it by value-matching to
  DBnomics; only ~201/258 codes resolve unambiguously (ties on shared values are left raw in
  `COMP_BREAKDOWN_1`). Data360 is kept as an independent **cross-validation**, not the primary.
- DBnomics mirror also covers slightly more (127 vs 116 reporters).

## Indicator codes (DBnomics `IMF/CDIS`)
- `IOW_BP6_USD` — Outward Direct Investment Positions, USD (total, all instruments)
- `IIW_BP6_USD` — Inward Direct Investment Positions, USD (total) — used for mirror
- Series code pattern: `A.<REF_AREA>.<INDICATOR>.<COUNTERPART_AREA>` (China = `CN`)
- 110 indicators exist (equity vs debt, gross vs net, derived, EUR/USD/domestic) — see
  https://db.nomics.world/IMF/CDIS

## Comparison to the BU greenfield data (context)
- **CDIS**: official bilateral FDI *stocks*, all FDI types, 2009+, near-complete via mirror.
- **BU (`bu_*_fdi.csv`)**: project-level *greenfield only*, announced amounts sparse
  (~15% of Asia deals verified), but goes back to ~2000 and is deal-granular.
Pick CDIS for a clean official China→country control (2009+, stocks); keep BU for
greenfield-specific, pre-2009, or project-count measures.
