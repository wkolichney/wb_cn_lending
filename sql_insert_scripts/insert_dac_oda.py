"""
Load OECD DAC2A ODA disbursements (US$, from 2000) into dac_oda.

Source: OECD SDMX API (DAC2A, all donors x all recipients, USD). Recipient names are
resolved to iso3 through the country_alternate crosswalk (the single name authority --
see codebook/country_alternate.csv), the same pattern as insert_conflict.py /
insert_dsa_credit.py. Recipients that don't resolve (regional / income aggregates,
multilateral channels) are written to dac_unmatched_recipients.csv for review and then
dropped, satisfying the FK to country(iso3).

Idempotent: clears dac_oda first so the script can be re-run.
"""
from pathlib import Path

import pandas as pd
import requests
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

SCRIPT_DIR = Path(__file__).resolve().parent

# --- pull DAC2A from the OECD SDMX API -------------------------------------
url = "https://sdmx.oecd.org/public/rest/data/OECD.DCD.FSD,DSD_DAC2@DF_DAC2A,/..206.USD.Q"
response = requests.get(url, params={"startPeriod": "2000"}, headers={"Accept": "application/json"})
response.raise_for_status()
data = response.json()

structure = data["structure"]
series_list = data["dataSets"][0]["series"]
dimensions = structure["dimensions"]["series"]
dim_values = {d["id"]: {str(i): v["name"] for i, v in enumerate(d["values"])} for d in dimensions}
time_periods = [t["id"] for t in structure["dimensions"]["observation"][0]["values"]]

rows = []
for key, series in series_list.items():
    key_parts = key.split(":")
    dim_labels = {d["id"]: dim_values[d["id"]][key_parts[i]] for i, d in enumerate(dimensions)}
    for obs_idx, obs_vals in series["observations"].items():
        rows.append({**dim_labels, "period": time_periods[int(obs_idx)], "value": obs_vals[0]})
df = pd.DataFrame(rows)

# --- resolve recipient -> iso3 via the crosswalk ---------------------------
country_name = pd.read_sql(
    'SELECT iso3, countryshortname FROM country_alternate WHERE iso3 IS NOT NULL', con=engine)

# diagnostic: recipients the crosswalk can't resolve (aggregates / multilateral
# channels). Add any genuine country spelling to codebook/country_alternate.csv and
# re-run insert_country_alternate.py; the rest are intentionally dropped.
unmatched = sorted(set(df['RECIPIENT']) - set(country_name['countryshortname']))
if unmatched:
    pd.Series(unmatched, name='RECIPIENT').to_csv(
        SCRIPT_DIR / 'dac_unmatched_recipients.csv', index=False, encoding='utf-8-sig')
    print(f'{len(unmatched)} unmatched recipient name(s) -> dac_unmatched_recipients.csv (dropped)')

merged = df.merge(country_name, left_on='RECIPIENT', right_on='countryshortname', how='inner')
out = merged.rename(columns={'DONOR': 'donor', 'period': 'year'})[['donor', 'iso3', 'year', 'value']]

# clear first so re-running doesn't double-insert
with engine.begin() as conn:
    conn.execute(text('DELETE FROM dac_oda'))

out.to_sql('dac_oda', con=engine, if_exists='append', index=False)
print(f'Inserted {len(out)} donor x recipient x year rows into dac_oda '
      f'({out["iso3"].nunique()} recipient countries)')
