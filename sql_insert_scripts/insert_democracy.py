from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

df = pd.read_excel(MANUAL_DIR / 'p5v2018.xls')

df_copy = df[['country', 'year', 'polity2']].copy()
df_copy['country'] = df_copy['country'].str.strip()
df_copy['polity2'] = df_copy['polity2'].astype('Int64')

# Resolve Polity's country name -> iso3 via the country_alternate lookup (plus the
# canonical country.countryshortname). All name->iso3 knowledge lives in
# country_alternate -- run insert_polity_country_alternate.py first so Polity's
# spellings are registered. Names that don't resolve (historical states,
# non-borrower countries) are dropped, satisfying the FK to country(iso3).
cs = pd.read_sql("SELECT countryshortname, iso3 FROM country WHERE iso3 IS NOT NULL", engine)
alt = pd.read_sql("SELECT countryshortname, iso3 FROM country_alternate WHERE iso3 IS NOT NULL", engine)
lookup = pd.concat([cs, alt], ignore_index=True)
lookup['countryshortname'] = lookup['countryshortname'].str.strip()
lookup = lookup.drop_duplicates(subset='countryshortname')

merged = df_copy.merge(lookup, left_on='country', right_on='countryshortname', how='left')

before = len(merged)
resolved = merged.dropna(subset=['iso3'])
print(f"Dropped {before - len(resolved)} rows without a matching country; inserting {len(resolved)}.")

# Clear existing rows so re-running this script doesn't double-insert.
with engine.begin() as conn:
    conn.execute(text("DELETE FROM democracy"))

resolved[['iso3', 'year', 'polity2']].to_sql(
    'democracy', con=engine, if_exists='append', index=False)
