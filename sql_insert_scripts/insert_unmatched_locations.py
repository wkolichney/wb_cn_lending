"""
Fold reconciled UCDP location spellings back into country_alternate.

insert_conflict.py writes names it can't resolve to unmatched_locations.csv. After a
human fills the `iso3` column for the names worth keeping (blank = intentionally
discarded, e.g. historical entities pre-2000), this script appends each filled-in
spelling to country_alternate so future joins on that name resolve to one iso3.

iso2 is borrowed from an existing country_alternate row for the same iso3 (the table
already carries it; the country table doesn't). Re-runnable: rows whose spelling is
already present (UNIQUE uq_alt_name) are skipped.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

UNMATCHED_PATH = Path(__file__).parent / 'unmatched_locations.csv'

# only the rows a human gave an iso3
new = pd.read_csv(UNMATCHED_PATH, dtype=str).dropna(subset=['iso3'])
new = new.rename(columns={'location': 'countryshortname'})
new['countryshortname'] = new['countryshortname'].str.strip()

existing = pd.read_sql(
    'SELECT iso3, iso2, countryshortname FROM country_alternate', con=engine
)

# FK safety: iso3 must already exist in country_alternate (and therefore country)
known_iso3 = set(existing['iso3'].dropna())
bad = sorted(set(new['iso3']) - known_iso3)
if bad:
    print(f'Skipping unknown iso3 (not in country_alternate): {bad}')
    new = new[new['iso3'].isin(known_iso3)]

# borrow iso2 from any existing row for that iso3
iso2_by_iso3 = (
    existing.dropna(subset=['iso2']).drop_duplicates('iso3').set_index('iso3')['iso2']
)
new['iso2'] = new['iso3'].map(iso2_by_iso3)

# idempotent: drop spellings already in the table (UNIQUE key on countryshortname)
new = new[~new['countryshortname'].isin(set(existing['countryshortname']))]

if new.empty:
    print('Nothing to insert -- all filled-in spellings already in country_alternate.')
else:
    new[['iso3', 'iso2', 'countryshortname']].to_sql(
        'country_alternate', con=engine, if_exists='append', index=False
    )
    print(f'Inserted {len(new)} spelling(s) into country_alternate:')
    print(new[['countryshortname', 'iso3', 'iso2']].to_string(index=False))
