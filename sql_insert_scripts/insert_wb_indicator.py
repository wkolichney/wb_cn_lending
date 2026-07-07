"""   
Insert unique developer indicator codes to its own lookup table, made in sql
Then for each country, do the api pull for years 2000-2024, for each of the devleopment indicators in the methodology


"""
import pandas as pd
from bblocks.data_importers import WorldBank
from sqlalchemy import create_engine, text
import time


engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')
wb = WorldBank()
indicators = wb.get_available_indicators()
iso = pd.read_sql("SELECT DISTINCT iso3 FROM country WHERE iso3 IS NOT NULL", con = engine)
indicators.to_sql('wb_indicators', con=engine, if_exists='append', index=False)


indicators_look = [
    'NY.GDP.TOTL.RT.ZS',
    'BX.KLT.DINV.WD.GD.ZS',
    'DT.DOD.DECT.GN.ZS',
    'NY.GDP.PCAP.KD',
    'NY.GDP.MKTP.KD.ZG',
    'SP.POP.TOTL',
    'NE.TRD.GNFS.ZS',
    'FP.CPI.TOTL.ZG',
    'NY.GDP.MKTP.KD'
]

results = []

for indicator in indicators_look:
    try:
        df_temp = wb.get_data(
            indicator_code=indicator,        # one at a time
            entity_code=iso['iso3'].tolist(),
            start_year=2000,
            end_year=2024,
            skip_aggs=True,
            skip_blanks=True,
            include_labels=True,
        )
        results.append(df_temp)
        print(f"✓ {indicator} — {len(df_temp)} rows")
    except Exception as e:
        print(f"✗ {indicator} — failed: {e}")
    
    time.sleep(1)  # be polite to the API

df = pd.concat(results, ignore_index=True)

df = df[['value','indicator_code','entity_code','year']]
df.rename(columns={'entity_code': 'iso3'}, inplace=True)
df.to_sql('wb_indicator_pull', con=engine, if_exists='append', index=False)
