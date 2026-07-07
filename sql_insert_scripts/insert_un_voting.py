"""  
Each country (for which we have wb project data for) needs to have a control variable for their UN agreement with the US and China

Will use Dyadic ideal point distance with China and in UNGA doi:10.7910/DVN/LEJUQZ
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'

iso_db = pd.read_sql('SELECT DISTINCT iso3 FROM country', con = engine)


df = pd.read_csv(MANUAL_DIR / 'AgreementScores.csv')
df = df.drop(columns='Unnamed: 0')



# includes iso3, use to link iso to COW
iso_cow = pd.read_csv(MANUAL_DIR / 'IdealPointDyads1946-2025.csv')

iso_cow_pairing = iso_cow[['ccode1', 'iso3c1']].drop_duplicates()
iso_cow_pairing = iso_cow_pairing.rename(columns={'iso3c1': 'iso', 'ccode1': 'ccode'})
iso_cow_pairing[(iso_cow_pairing['iso'] == 'CHN') | (iso_cow_pairing['iso'] == 'USA')]


cn_df = df[(df['ccode2'] == 710) | (df['ccode2'] == 2)] #interested in UN voting agreeance with US and China, these are our counterparts
cn_df['ccode2'] = cn_df['ccode2'].replace({710: 'CHN', 2: 'USA'}) #rename from COW to iso3
cn_df = cn_df[['ccode1', 'ccode2', 'year','agree','IdealPointDistance']] #columsn for our db. Unsure what IdealPointDistance, so keeping for now
cn_df = cn_df.merge(iso_cow_pairing, left_on= 'ccode1', right_on = 'ccode', how = 'left') #get iso for all the other countries
cn_df = cn_df.drop(columns = ['ccode1', 'ccode']) #dont need COW codes for countries anymore
cn_df = cn_df.dropna() #don't want nulls (will mess up insert to sql)
cn_df = cn_df.rename(columns = {'iso': 'iso3', 'IdealPointDistance': 'ideal_point_distance', 'ccode2': 'us_china'}) # rename for sql

# only use countries that we have wb project data for
cn_df = cn_df[cn_df['iso3'].isin(iso_db['iso3'])]

#insert to db
cn_df.to_sql(name='un_cn_agree', con=engine, if_exists='append', index=False)