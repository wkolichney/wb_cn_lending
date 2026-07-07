"""
Load each country's goods exports TO China (and export share of GDP) into trade_china.

Sources:
  - Exports: IMF IMTS "Exports of goods, FOB, US dollar" (annual), summed across the
    three Chinas -- Mainland + Hong Kong SAR + Macao SAR (Taiwan excluded).
    File: manual_file_location/IMF_IMTS_china_exports.csv (SERIES_CODE[:3] is ISO3).
  - GDP: World Bank NY.GDP.MKTP.KD (constant 2015 US$), read from wb_indicator_pull.

PREREQUISITE: run insert_wb_indicator.py first -- GDP is joined from wb_indicator_pull.
Idempotent: clears trade_china first so the script can be re-run.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

# --- exports to China (IMF IMTS, wide) -------------------------------------
df = pd.read_csv(MANUAL_DIR / 'IMF_IMTS_china_exports.csv')

china_counterparts = [
    "China, People's Republic of",
    "Hong Kong Special Administrative Region, People's Republic of China",
    "Macao Special Administrative Region, People's Republic of China",
]
df = df[
    (df['FREQUENCY'] == 'Annual')
    & (df['INDICATOR'] == 'Exports of goods, Free on board (FOB), US dollar')
    & (df['COUNTERPART_COUNTRY'].isin(china_counterparts))
].copy()

# reporter ISO3 is the first 3 chars of SERIES_CODE
df['iso3'] = df['SERIES_CODE'].str[:3]

# wide year columns are the all-digit headers (e.g. '2019'); quarterly/monthly
# columns contain non-digits and are excluded automatically.
year_cols = [c for c in df.columns if str(c).isdigit()]

# sum the three Chinas per reporter-year (min_count=1 keeps NaN if none reported)
exports = (
    df.groupby('iso3')[year_cols].sum(min_count=1).reset_index()
    .melt(id_vars='iso3', value_vars=year_cols, var_name='year', value_name='exports')
)
exports['year'] = exports['year'].astype(int)
exports['exports'] = exports['exports'] * 1_000_000  # source unit is millions of USD

# --- GDP (constant 2015 US$) from the WB indicator pull --------------------
gdp = pd.read_sql(
    "SELECT iso3, year, value AS `gdp$2015` "
    "FROM wb_indicator_pull WHERE indicator_code = 'NY.GDP.MKTP.KD'",
    con=engine,
)

# inner join keeps only country-years with both exports and GDP
both = exports.merge(gdp, on=['iso3', 'year'])
both['export%gdp'] = (both['exports'] / both['gdp$2015']) * 100

# FK safety: iso3 must exist in country (GDP already comes from in-db iso3)
valid_iso3 = pd.read_sql('SELECT iso3 FROM country WHERE iso3 IS NOT NULL', con=engine)['iso3']
both = both[both['iso3'].isin(valid_iso3)]

# clear first so re-running doesn't double-insert
with engine.begin() as conn:
    conn.execute(text('DELETE FROM trade_china'))

both[['iso3', 'year', 'exports', 'gdp$2015', 'export%gdp']].to_sql(
    'trade_china', con=engine, if_exists='append', index=False)
print(f'Inserted {len(both)} country-year rows into trade_china '
      f'({both["iso3"].nunique()} countries, {both["year"].min()}-{both["year"].max()})')
