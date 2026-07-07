from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

# Political corruption: V-Dem Public sector corruption index (v2x_pubcorr),
# Coppedge et al. (2017), V-Dem-CY-Core v16. Range 0-1, higher = more corrupt.
df = pd.read_csv(MANUAL_DIR / 'V-Dem-CY-Core-v16.csv',
                 usecols=['country_text_id', 'year', 'v2x_pubcorr'],
                 low_memory=False)

# V-Dem's country_text_id is already ISO3 for every state that overlaps our
# `country` table, so no country_alternate name-mapping is needed -- we join
# directly on iso3. Codes with no match are either non-borrower countries
# (USA, GBR, DEU, Gulf states, ...) or historical/contested entities (DDR, ZZB,
# Papal States, ...); those rows are dropped, satisfying the FK to country(iso3).
df = df.rename(columns={'country_text_id': 'iso3'})
df = df.dropna(subset=['v2x_pubcorr'])

valid_iso3 = set(pd.read_sql("SELECT iso3 FROM country WHERE iso3 IS NOT NULL", engine)['iso3'])
before = len(df)
resolved = df[df['iso3'].isin(valid_iso3)]
print(f"Dropped {before - len(resolved)} rows without a matching country; inserting {len(resolved)}.")

# Clear existing rows so re-running this script doesn't double-insert.
with engine.begin() as conn:
    conn.execute(text("DELETE FROM corruption"))

resolved[['iso3', 'year', 'v2x_pubcorr']].to_sql(
    'corruption', con=engine, if_exists='append', index=False)
