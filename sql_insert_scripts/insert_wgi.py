import pandas as pd
from sqlalchemy import create_engine
import wbgapi as wb
engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

"""  
Insert WB governance indicators. We get to use the same tables as we did for development indicators

"""


wb.db = 3 #wgi
iso = pd.read_sql('SELECT DISTINCT iso3 FROM country', con=engine)['iso3'].dropna().tolist()

"""  
World Bank WGI
GOV_WGI_PV.EST	Political Stability - Governance estimate (approx. -2.5 to +2.5)
GOV_WGI_GE.EST	Government Effectiveness - Governance estimate (approx. -2.5 to +2.5)
"""

wb.db = 3
wb.series.info()
indicator_code = [
    'GOV_WGI_PV.EST',
    'GOV_WGI_GE.EST'
]

df = wb.data.DataFrame(indicator_code, iso, range(2000,2025), labels = True, columns = 'series').reset_index()

df_indicator = pd.DataFrame({
    "indicator_code": ["GOV_WGI_GE.EST", "GOV_WGI_PV.EST"],
    "indicator_name": ["Government Effectiveness - Governance estimate (approx. -2.5 to +2.5)",
              "Political Stability - Governance estimate (approx. -2.5 to +2.5)"]
})

df_long = df.melt(
    id_vars=["economy", "Time", "Country"],
    value_vars=["GOV_WGI_GE.EST", "GOV_WGI_PV.EST"],
    var_name="indicator_code",
    value_name="value"
).rename(columns={"economy": "iso3", "Time": "year"})

# reorder columns to match
df_long = df_long[["value", "indicator_code", "iso3", "year"]]


# Insert parent table first, then child
df_indicator.to_sql('wb_indicators', con=engine, if_exists='append', index=False)
df_long.to_sql('wb_indicator_pull', con=engine, if_exists='append', index=False)