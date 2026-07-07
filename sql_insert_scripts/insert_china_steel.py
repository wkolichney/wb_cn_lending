import pandas as pd
from sqlalchemy import create_engine, text
import requests

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')


# API PULL

url = "https://chinadata.live/api/v2/data/steel-production-china-vs-world"
response = requests.get(url)
response.raise_for_status()

# Parse JSON and extract the data array
json_data = response.json()
records = json_data["data"]["data"]

# Load into DataFrame
df = pd.DataFrame(records)

# rename for sql table
rename_df = df.rename(columns={
    'date': 'year',
    'china': 'china_steel',
    'world_total': 'world_steel',
})

#insert sql
rename_df.to_sql(name='china_steel', con=engine, if_exists='append', index=False)