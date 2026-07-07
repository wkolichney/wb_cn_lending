"""
Load oil & gas production/value into oil_gas.

Source: Ross-Mahdavi Oil and Gas 1932-2014 (see manual_file_location/README.md).
The dataset's `id` column is already ISO3, so we join directly on iso3 -- no
country_alternate name mapping is needed. Codes with no match in the country table
(non-borrower / historical entities) are dropped, satisfying the FK to country(iso3).

Idempotent: clears oil_gas first so the script can be re-run.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

country_iso = pd.read_sql('SELECT iso3 FROM country WHERE iso3 IS NOT NULL', con=engine)

df = pd.read_csv(MANUAL_DIR / 'Ross-Mahdavi Oil and Gas 1932-2014.csv')

df = df[['id', 'year', 'oil_prod32_14', 'oil_value_2014', 'gas_prod55_14', 'gas_value_2014']].rename(
    columns={
        'id':             'iso3',
        'oil_prod32_14':  'oil_prod',
        'oil_value_2014': 'oil_value',
        'gas_prod55_14':  'gas_prod',
        'gas_value_2014': 'gas_value',
    }
)

# FK safety: only keep iso3 already present in the country table
before = len(df)
df = df[df['iso3'].isin(country_iso['iso3'])]
print(f'Dropped {before - len(df)} rows without a matching country; inserting {len(df)}.')

# clear first so re-running doesn't double-insert
with engine.begin() as conn:
    conn.execute(text('DELETE FROM oil_gas'))

df.to_sql('oil_gas', con=engine, if_exists='append', index=False)
print(f'Inserted {len(df)} oil/gas country-year rows ({df["iso3"].nunique()} countries)')
