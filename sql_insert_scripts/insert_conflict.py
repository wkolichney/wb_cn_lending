"""
Load the UCDP/PRIO Armed Conflict Dataset (ACD) v26.1 into wb_proj_doc.ucdp_conflict.

Source: UcdpPrioConflict_v26_1.csv (conflict-year panel, 1946-2025).
Loads only the lean country-year subset of columns. Run conflict.sql first.

The source identifies countries by `location` (name; comma-separated for interstate
conflicts). We split + explode `location` into one row per country, then resolve each
name to iso3 by an inner merge against country_alternate (same pattern as
insert_dsa_credit.py / fdi_imf.py). UCDP-specific spellings that don't match are first
normalized via UCDP_NAME_FIX; whatever still fails to match is written to
unmatched_locations.csv for manual review (extend UCDP_NAME_FIX or accept the discard).

Missing data in the source is coded -99 and, for several fields, as blanks.
Both are mapped to NULL here so they don't get inserted as the literal
-99 / empty string.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

CSV_PATH = Path(__file__).parent.parent / 'manual_file_location' / 'UcdpPrioConflict_v26_1.csv'
UNMATCHED_PATH = Path(__file__).parent / 'unmatched_locations.csv'

# Lean country-year subset kept from the CSV (conflict_year_id is AUTO_INCREMENT;
# iso3 is derived from location below). Join is by location name, not gwno.
COLS = [
    'conflict_id', 'location', 'year', 'incompatibility',
    'intensity_level', 'cumulative_intensity', 'type_of_conflict',
]

# Integer columns -- nullable, so use pandas' Int64 to keep NULLs as <NA>.
INT_COLS = [
    'conflict_id', 'year', 'incompatibility', 'intensity_level',
    'cumulative_intensity', 'type_of_conflict',
]

# UCDP uses parenthetical / historical spellings that don't match country_alternate.
# Map the UCDP `location` spelling -> a name that country_alternate knows. Extend this
# from unmatched_locations.csv as needed. (Pre-2000 historical entities such as
# 'Russia (Soviet Union)', 'South Vietnam', 'South Yemen', 'Hyderabad' are intentionally
# left unmapped -- they are discarded, since the regression export filters year >= 2000.)
UCDP_NAME_FIX = {
    'Myanmar (Burma)': 'Myanmar',
    'Cambodia (Kampuchea)': 'Cambodia',
    'DR Congo (Zaire)': 'Congo, Democratic Republic of',
    'Serbia (Yugoslavia)': 'Serbia',
    'Zimbabwe (Rhodesia)': 'Zimbabwe',
    'Madagascar (Malagasy)': 'Madagascar',
}

# read everything as string first so -99 / blanks are handled uniformly
df = pd.read_csv(CSV_PATH, dtype=str, keep_default_na=False)[COLS]

# blanks and the -99 missing-data sentinel -> NULL
df = df.replace({'': pd.NA, '-99': pd.NA})

# nullable integers
for c in INT_COLS:
    df[c] = pd.to_numeric(df[c], errors='coerce').astype('Int64')

# explode interstate conflicts: location is a comma-separated list of countries
# (UCDP never puts a comma inside a single country name), so one row per country.
df['location'] = df['location'].str.split(', ')
df = df.explode('location', ignore_index=True)

# normalize UCDP-specific spellings, then resolve to iso3 via country_alternate
df['location'] = df['location'].replace(UCDP_NAME_FIX)

country_name = pd.read_sql(
    'SELECT iso3, countryshortname FROM country_alternate WHERE iso3 IS NOT NULL',
    con=engine,
)

# diagnostic: surface names that won't resolve so they can be reviewed (mirrors
# insert_iso3_country.py's country_check.csv). Re-runnable.
unmatched = sorted(set(df['location'].dropna()) - set(country_name['countryshortname']))
if unmatched:
    pd.Series(unmatched, name='location').to_csv(UNMATCHED_PATH, index=False)
    print(f'{len(unmatched)} unmatched location name(s) -> {UNMATCHED_PATH.name} '
          f'(discarded). Add post-2000 misses to UCDP_NAME_FIX and re-run.')

# inner merge drops unmatched / non-borrower names (same as insert_dsa_credit.py)
df = df.merge(
    country_name, left_on='location', right_on='countryshortname', how='inner'
).drop(columns='countryshortname')

# insert to sql -- clear first so the script is idempotent / re-runnable
with engine.begin() as conn:
    conn.execute(text('DELETE FROM ucdp_conflict'))

df.to_sql('ucdp_conflict', con=engine, if_exists='append', index=False)
print(f'Inserted {len(df)} conflict x year x country rows into ucdp_conflict '
      f'({df["iso3"].nunique()} countries)')
