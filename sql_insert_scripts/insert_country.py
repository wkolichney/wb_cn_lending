import pandas as pd
import pandas as pd
from sqlalchemy import create_engine
import requests
import json
import pandas as pd
import wbgapi as wb
import time
import sys
sys.path.append('..')  # Add the parent directory to the system path

from object import DOCUMENT_URL, PROJECT_URL, PROJECT_COLUMNS, COUNTRY_COLUMNS
from function import get_project
# Create the database engine
engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')


all_projects = {col: [] for col in COUNTRY_COLUMNS}  # ← init with same structure
offset = 0
total = 27848 #do 1000 for testing, but total is 27848

while offset < total:
    data = get_project(COUNTRY_COLUMNS, rows=1000, os=offset)
    if data is None:
        print(f"Skipping offset={offset} after failed retries")
        offset += 1000
        continue

    good_data = data['projects']

    for proj_id, proj in good_data.items():
        for col in COUNTRY_COLUMNS:
            all_projects[col].append(proj.get(col))  # ← append directly into all_projects

    offset += 1000

print(f"Done: {len(next(iter(all_projects.values())))} projects")

country_df = pd.DataFrame(all_projects)

############### INSERT INTO SQL ##################

#step 1: insert into country table
country_df = country_df[['countryshortname', 'regionname']].copy()
mask = country_df['countryshortname'] == country_df['regionname']
country_df.loc[mask, 'regionname'] = None
country_df = country_df.drop_duplicates(subset=['countryshortname'])
country_df.to_sql('country', con=engine, if_exists='append', index=False)