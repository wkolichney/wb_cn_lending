from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

df_dsa = pd.read_excel(MANUAL_DIR / 'debt_data_portal_datasets.xls', sheet_name='IMF risk analysis of countries')
df_rate = pd.read_excel(MANUAL_DIR / 'ratings.xlsx', sheet_name='rating')
df_rate_lookup = pd.read_excel(MANUAL_DIR / 'ratings.xlsx', sheet_name='lookup')


# country_alternate already holds the reconciled DSA spellings
# (see fix_dsa_country_names.py -- already run). Inner merge resolves
# Country -> iso3 and drops countries not in our country table (advanced
# economies such as Canada/Germany that aren't WB borrowers).
country_name = pd.read_sql('SELECT iso3, countryshortname FROM country_alternate', con=engine)
df_dsa_iso = df_dsa.merge(
    country_name, left_on='Country', right_on='countryshortname', how='inner'
).drop(columns=['Country', 'countryshortname'])

# Melt years wide->long; keep only rows that actually carry a rating.
df_dsa_iso_long = df_dsa_iso.melt(
    id_vars=['iso3'], var_name='year', value_name='dsa'
).dropna(subset=['dsa'])
df_dsa_iso_long['year'] = df_dsa_iso_long['year'].astype(int)

# df_rate is a dyadic (origin x destination x year) table, but the sovereign
# credit rating only depends on the rated country (iso3_d) and year -- it is
# identical across all origins. Collapse to one credit_id per (iso3, year).
# `rating` is the rating_id (1-22), i.e. the credit_lookup foreign key.
df_credit = (
    df_rate.dropna(subset=['rating'])
    .groupby(['iso3_d', 'year'], as_index=False)['rating'].first()
    .rename(columns={'iso3_d': 'iso3', 'rating': 'credit_id'})
)
df_credit['credit_id'] = df_credit['credit_id'].astype(int)

# Attach the credit_id FK. Left merge keeps every DSA row; credit_id stays NULL
# for country-years the ratings panel doesn't cover (it ends in 2023; DSA runs
# to 2026), which the nullable FK column allows.
df_dsa_iso_long = df_dsa_iso_long.merge(df_credit, on=['iso3', 'year'], how='left')
df_dsa_iso_long['credit_id'] = df_dsa_iso_long['credit_id'].astype('Int64')

# Align lookup-sheet headers with the credit_lookup table columns.
df_rate_lookup = df_rate_lookup.rename(columns={
    'rating_id': 'credit_id',
    'S&P': 's_p',
    "Moody's": 'moody',
    'Fitch': 'fitch',
})

# insert to sql -- clear first (FK-safe order: child before parent) so the
# script is idempotent and can be re-run to repair an earlier partial load.
with engine.begin() as conn:
    conn.execute(text('DELETE FROM dsa_credit'))
    conn.execute(text('DELETE FROM credit_lookup'))

df_rate_lookup.to_sql('credit_lookup', con=engine, if_exists='append', index=False)
df_dsa_iso_long.to_sql('dsa_credit', con=engine, if_exists='append', index=False)
