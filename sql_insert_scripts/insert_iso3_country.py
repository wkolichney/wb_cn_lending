"""
Purpose: world bank project API doesn't use ISO for countries and the naming can vary across other world bank datasources
Since we need world bank indicators, lets align iso3 for api pull
"""
import pandas as pd
from bblocks.data_importers import WorldBank
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

wb = WorldBank()
indicators = wb.get_available_indicators()
entities = wb.get_available_entities()

proj_country = pd.read_sql("SELECT DISTINCT countryshortname FROM country", con = engine)

# MANUAL CHECK COUNTRY NAME MISMATCH #
entity_check = proj_country[~proj_country['countryshortname'].isin(entities['entity_name'])][['countryshortname']]
entity_check.to_csv('country_check.csv', index = False)


# countries that had to be fixed manually 6/2/2026
country_map = {
    'Caribbean': 'CSS', #wbi lists it as 'Carribean small states'
    'Congo, Democratic Republic of': 'COD',
    'Congo, Republic of': 'COG',
    'East Asia and Pacific': 'EAS',
    'Eastern and Southern Africa': 'AFE',
    'Egypt, Arab Republic of': 'EGY',
    'Europe and Central Asia': 'ECS',
    'Iran, Islamic Republic of': 'IRN',
    'Korea, Republic of': 'KOR',
    "Lao People's Democratic Republic": 'LAO',
    'Latin America and Caribbean': 'LCN',
    'Micronesia, Federated States of': 'FSM',
    'Middle East and North Africa': 'MEA',
    'Pacific Islands': 'PSS',
    'Somalia': 'SOM',
    'Somalia, Federal Republic of': 'SOM',
    'St Maarten': 'SXM',
    'Venezuela, Republica Bolivariana de': 'VEN',
    'Western and Central Africa': 'AFW',
    'Yemen, Republic of': 'YEM'
}


wb_iso = entities[['entity_code','entity_name']]

df = proj_country.merge(wb_iso, left_on= 'countryshortname', right_on = 'entity_name', how = 'left')
df = df.drop(columns='entity_name')
df['entity_code'] = df['entity_code'].fillna(df['countryshortname'].map(country_map))
df = df[df['countryshortname'] != 'Somalia, Federal Republic of'] # i want to get rid of this type of naming
df = df.rename(columns={'entity_code': 'iso3'})

#insert iso3 to country table
with engine.begin() as conn:
    for _, row in df[['countryshortname', 'iso3']].dropna(subset=['iso3']).iterrows():
        conn.execute(text("""
            UPDATE country 
            SET iso3 = :iso3 
            WHERE countryshortname = :name
        """), {"iso3": row['iso3'], "name": row['countryshortname']})