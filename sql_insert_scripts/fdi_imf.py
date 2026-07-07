"""
Insert China's bilateral FDI into bilateral_fdi.

Source: IMF Coordinated Direct Investment Survey (CDIS), wide format.
Slice we keep:
  - Counterpart = China (Mainland + Hong Kong + Macao, summed; Taiwan excluded)
  - Direction   = Inward  (REF_AREA country reports direct investment received from China)
  - Indicator   = "Direct Investment Positions" (headline, as directly reported)
Only countries already present in the `country` table are inserted (FK bilateral_fdi.iso3 -> country.iso3).
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

# iso3 we already have project data for
db_iso = pd.read_sql('SELECT DISTINCT iso3 FROM country', con=engine)

df = pd.read_csv(MANUAL_DIR / 'IMF_CDIS_WIDEF.csv')

china_labels = [
    'Counterpart: China, P.R.: Mainland',
    'Counterpart: China, P.R.: Hong Kong',
    'Counterpart: China, P.R.: Macao',
]

mask = (
    df['COMP_BREAKDOWN_1_LABEL'].isin(china_labels)
    & (df['COMP_BREAKDOWN_2_LABEL'] == 'Direction of investment: Inward')
    & (df['INDICATOR_LABEL'] == 'Direct Investment Positions')
)
cn = df[mask].copy()

# year columns are the numeric headers (2009..2023)
year_cols = [c for c in cn.columns if c.isdigit()]

long = cn.melt(
    id_vars=['REF_AREA'],
    value_vars=year_cols,
    var_name='year',
    value_name='flow',
)
long['year'] = long['year'].astype(int)

# sum Mainland + Hong Kong + Macao for each country-year; keep NaN if none reported (min_count=1)
long = (
    long.groupby(['REF_AREA', 'year'], as_index=False)['flow']
        .sum(min_count=1)
)

long = long.rename(columns={'REF_AREA': 'iso3'})
long = long.dropna(subset=['flow'])

# drop China-into-China (self-referential): we want China's flow *to* other countries
long = long[long['iso3'] != 'CHN']

# only countries we already have in the db (satisfies the FK)
long = long[long['iso3'].isin(db_iso['iso3'])]

print(f'rows to insert: {len(long)}  countries: {long["iso3"].nunique()}  years: {long["year"].min()}-{long["year"].max()}')

long[['year', 'flow', 'iso3']].to_sql(name='bilateral_fdi', con=engine, if_exists='append', index=False)
