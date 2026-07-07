"""
Load the published country-name crosswalk into the `country_alternate` table.

External data sources spell country names differently than the World Bank project
API's canonical `countryshortname`. `country_alternate` is a long lookup mapping every
known spelling -> one iso3, so any future source join resolves to a single country.

SOURCE OF TRUTH: codebook/country_alternate.csv (published crosswalk, one row per
spelling). To register a spelling for a new source, add a row there and re-run this
script -- do NOT edit the table by hand. See codebook/README.md for the column spec and
how the crosswalk was originally constructed (the one-time build scripts are archived
under archive/drafting/).

Conventions in the CSV:
    real 3-letter iso3   -> in scope; maps the spelling to that country
    blank iso3           -> in-scope aggregate region with no country code (e.g. Africa);
                            stored with iso3 = NULL, resolves on name only

Idempotent: clears country_alternate first, so the table always mirrors the CSV.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

CROSSWALK_CSV = Path(__file__).resolve().parent.parent / 'codebook' / 'country_alternate.csv'

# utf-8-sig strips the BOM Excel may have added. Read as string so blank iso3/iso2
# stay blank (we convert them to real NULLs below rather than pandas' NaN games).
alt = pd.read_csv(CROSSWALK_CSV, encoding='utf-8-sig', dtype=str, keep_default_na=False)

for col in ['iso3', 'iso2', 'countryshortname']:
    alt[col] = alt[col].str.strip()

# blank iso3/iso2 -> real NULL; drop rows with no spelling; one row per spelling
alt['iso3'] = alt['iso3'].replace('', pd.NA)
alt['iso2'] = alt['iso2'].replace('', pd.NA)
alt = alt[alt['countryshortname'] != '']
alt = alt.drop_duplicates(subset='countryshortname')

# a spelling must resolve to ONE place -- surface any conflicts before loading
conflicts = alt.dropna(subset=['iso3']).groupby('countryshortname')['iso3'].nunique()
conflicts = conflicts[conflicts > 1]
if len(conflicts):
    print('WARNING: these spellings map to multiple iso3 (fix codebook/country_alternate.csv):')
    print(conflicts)

# FK safety: a non-null iso3 must already exist in country; null iso3 (regions) is fine
valid_iso3 = pd.read_sql('SELECT iso3 FROM country WHERE iso3 IS NOT NULL', con=engine)['iso3']
keep = alt['iso3'].isna() | alt['iso3'].isin(valid_iso3)
if (~keep).any():
    print('Dropping rows whose iso3 is not in the country table (run insert_iso3_country.py first?):')
    print(alt.loc[~keep, ['iso3', 'countryshortname']].to_string(index=False))
alt = alt[keep]

# reload: clear then insert so the table always matches the CSV
with engine.begin() as conn:
    conn.execute(text('DELETE FROM country_alternate'))
alt[['iso3', 'iso2', 'countryshortname']].to_sql(
    'country_alternate', con=engine, if_exists='append', index=False)

print(f'Loaded {len(alt)} alternate names '
      f'({alt["iso3"].notna().sum()} with iso3, {alt["iso3"].isna().sum()} region/no-iso3)')
