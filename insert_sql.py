import pandas as pd
from sqlalchemy import create_engine
import requests
import json
import pandas as pd
import wbgapi as wb
import time
from object import DOCUMENT_URL, PROJECT_URL, PROJECT_COLUMNS
from function import get_project

# Create the database engine
engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')


all_projects = {col: [] for col in PROJECT_COLUMNS}  # ← init with same structure
offset = 0
total = 1000 #do 1000 for testing, but total is 27848

while offset < total:
    data = get_project(PROJECT_URL, rows=1000, os=offset)
    if data is None:
        print(f"Skipping offset={offset} after failed retries")
        offset += 1000
        continue

    good_data = data['projects']

    for proj_id, proj in good_data.items():
        for col in PROJECT_COLUMNS:
            all_projects[col].append(proj.get(col))  # ← append directly into all_projects

    offset += 1000

print(f"Done: {len(next(iter(all_projects.values())))} projects")

proj_df = pd.DataFrame(all_projects)

############### INSERT INTO SQL ##################
