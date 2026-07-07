from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# Raw source files live at the repo root; countries_fixed.csv is a small manual
# reconciliation input kept next to this script.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'
SCRIPT_DIR = Path(__file__).resolve().parent

country_iso = pd.read_sql('SELECT iso3, countryshortname FROM country WHERE iso3 IS NOT NULL;', con = engine)

df_raw = pd.read_excel(MANUAL_DIR / '30802-0001-Data.xls', sheet_name='diplomaticrecognitiondatasetspr')

# Drop useless year dummy columns and countryid, keep taiwanrecognition
year_cols = [col for col in df_raw.columns if col.startswith('_')]
df = df_raw.drop(columns=year_cols + ['countryid'])

# Step 1: Split into matched and unmatched
country_match = df.merge(country_iso, left_on='country', right_on='countryshortname', how='inner')

no_match = df.merge(country_iso, left_on='country', right_on='countryshortname', how='left', indicator=True)
no_match = no_match[no_match['_merge'] == 'left_only'].drop(columns=['_merge', 'iso3', 'countryshortname'])

# Step 2: Export unmatched countries for manual fixing
no_match_unique = no_match[['country']].drop_duplicates()
no_match_unique['iso3'] = None
no_match_unique.to_csv(SCRIPT_DIR / 'countries_to_fix.csv', index=False)

# Step 3: Read back the manually fixed csv and merge iso3 onto unmatched rows
manual_fix = pd.read_csv(SCRIPT_DIR / 'countries_fixed.csv')
no_match_fixed = no_match.merge(manual_fix[['country', 'iso3']], on='country', how='left')

# Step 4: Combine and clean up
df_final = pd.concat([country_match, no_match_fixed], ignore_index=True)
df_final = df_final.drop(columns='countryshortname')

df_final = df_final[['year', 'iso3', 'taiwanrecognition']]
# where iso is null, is countires we don't need, like yugoslavia
df_final = df_final[df_final['iso3'].notna()]
# only use iso of countries we already have, otherwise sql error
df_final = df_final[df_final['iso3'].isin(country_iso['iso3'])]

df_final.to_sql(name='taiwan_recognition', con=engine, if_exists='append', index=False)