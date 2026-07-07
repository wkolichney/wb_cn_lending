# manual_file_location/

Raw source files that cannot be pulled from an API and must be downloaded by hand.
Every insert script resolves this directory portably as

```python
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'
```

so scripts run correctly regardless of the current working directory.

## Git policy

The raw files here are **git-ignored** — several are large (IMF CDIS ≈ 242 MB, V-Dem
≈ 212 MB) and some carry redistribution restrictions. Only this README is tracked.
To reproduce the database, download each file from the source below and drop it in this
folder with the **exact filename** listed (the scripts read files by name).

## Files

| File | Source | Consumed by |
|------|--------|-------------|
| `V-Dem-CY-Core-v16.csv` | V-Dem Country-Year Core v16 — v-dem.net/data/the-v-dem-dataset/ | `insert_corruption.py` |
| `UcdpPrioConflict_v26_1.csv` | UCDP/PRIO Armed Conflict Dataset v26.1 — ucdp.uu.se/downloads/ | `insert_conflict.py` |
| `p5v2018.xls` | Polity5 Annual Time-Series (p5v2018), Center for Systemic Peace — systemicpeace.org/inscrdata.html | `insert_democracy.py` |
| `AgreementScores.csv` | UN General Assembly voting agreement scores (Bailey/Strezhnev/Voeten) — Harvard Dataverse doi:10.7910/DVN/LEJUQZ | `insert_un_voting.py` |
| `IdealPointDyads1946-2025.csv` | UN ideal-point dyads (same Dataverse release) — doi:10.7910/DVN/LEJUQZ | `insert_un_voting.py` |
| `30802-0001-Data.xls` | Diplomatic recognition dataset, ICPSR study 30802 (sheet `diplomaticrecognitiondatasetspr`) — icpsr.umich.edu | `insert_taiwan_approval.py` |
| `IMF_CDIS_WIDEF.csv` | IMF Coordinated Direct Investment Survey (CDIS), wide format — data.imf.org | `fdi_imf.py` |
| `debt_data_portal_datasets.xls` | IMF Debt Sustainability Analysis risk ratings (sheet `IMF risk analysis of countries`) — imf.org | `insert_dsa_credit.py` |
| `ratings.xlsx` | Sovereign credit ratings crosswalk (sheets `rating`, `lookup`; S&P / Moody's / Fitch) | `insert_dsa_credit.py` |
| `GCI Database-Countries.csv` | GDP Center / Global China Initiative country reference table (ISO-2 ↔ ISO-3) | `insert_iso2.py` |
| `Ross-Mahdavi Oil and Gas 1932-2014.csv` | Ross–Mahdavi Oil and Gas Production and Value dataset, 1932–2014 (codebook PDF in `archive/drafting/oil_gas/`) | `insert_oil_gas.py` |
| `IMF_IMTS_china_exports.csv` | IMF International Merchandise Trade Statistics (IMTS) — exports of goods (FOB, USD) to China; data.imf.org. Renamed from its timestamped download name. | `insert_trade_china.py` |
| `DSA_LIC_EXPORT.xlsx`, `DSA_MAC_EXPORT.xlsx` | IMF/WB Debt Sustainability Framework exports (LIC / MAC) — used only in the archived crosswalk-construction step (`archive/drafting/validation/`) |  |

> Versions above are the ones used for the current build. If you download a newer
> vintage, expect new country spellings — add them to `codebook/country_alternate.csv`
> and re-run `insert_country_alternate.py`.
