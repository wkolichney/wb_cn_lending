import pandas as pd
from sqlalchemy import create_engine
import sys
sys.path.append('..')

from object import PROJECT_URL, PROJECT_COLUMNS, COUNTRY_COLUMNS, MAJOR_SECTOR_COLUMNS, SECTOR_COLUMNS
from function import get_project

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# collect ALL columns you need across all tables
ALL_COLUMNS = list(set(PROJECT_COLUMNS + COUNTRY_COLUMNS + ['regionname', 'major_sectors', 'borrower', 'impagency']))

all_projects = {col: [] for col in ALL_COLUMNS}
offset = 0
total = 27848

while offset < total:
    data = get_project(PROJECT_URL, rows=1000, os=offset)
    if data is None:
        print(f"Skipping offset={offset} after failed retries")
        offset += 1000
        continue

    good_data = data['projects']
    for proj_id, proj in good_data.items():
        for col in ALL_COLUMNS:
            all_projects[col].append(proj.get(col))

    offset += 1000

print(f"Done: {len(next(iter(all_projects.values())))} projects")

df = pd.DataFrame(all_projects)

# ── country ──────────────────────────────────────────
country_df = df[['countryshortname', 'regionname']].copy()
mask = country_df['countryshortname'] == country_df['regionname']
country_df.loc[mask, 'regionname'] = None
country_df = country_df.drop_duplicates(subset=['countryshortname']).dropna(subset=['countryshortname'])
country_df.to_sql('country', con=engine, if_exists='append', index=False)

# ── projects ──────────────────────────────────────────
projects_df = df[PROJECT_COLUMNS].copy()
projects_df = projects_df.rename(columns={'id': 'project_id'})
projects_df = projects_df.drop_duplicates(subset=['project_id'])
projects_df['boardapprovaldate'] = pd.to_datetime(projects_df['boardapprovaldate'], errors='coerce').dt.date
projects_df['closingdate'] = pd.to_datetime(projects_df['closingdate'], errors='coerce').dt.date
projects_df.to_sql('projects', con=engine, if_exists='append', index=False)

# ── borrower ──────────────────────────────────────────
borrower_rows = []
for _, row in df.iterrows():
    if pd.isna(row['borrower']):
        continue
    for name in str(row['borrower']).split(','):
        name = name.strip()
        if name:
            borrower_rows.append({'project_id': row['id'], 'borrower_name': name})

borrower_df = pd.DataFrame(borrower_rows)
borrower_df.to_sql('borrower', con=engine, if_exists='append', index=False)

# ── impagency ─────────────────────────────────────────
impagency_rows = []
for _, row in df.iterrows():
    if pd.isna(row['impagency']):
        continue
    for name in str(row['impagency']).split(','):
        name = name.strip()
        if name:
            impagency_rows.append({'project_id': row['id'], 'impagency_name': name})

impagency_df = pd.DataFrame(impagency_rows)
impagency_df.to_sql('impagency', con=engine, if_exists='append', index=False)

# ── major_sectors and sectors ─────────────────────────
major_sector_rows = []
sector_rows = []

for _, row in df.iterrows():
    proj_id = row['id']
    if not isinstance(row['major_sectors'], list):
        continue
    for ms_entry in row['major_sectors']:
        ms = ms_entry['major_sector']
        major_sector_rows.append({
            'major_sector_code': ms['major_sector_code'],
            'major_sector_name': ms['major_sector_name']
        })
        for sector in ms.get('sectors', []):
            sector_rows.append({
                'project_id': proj_id,
                'major_sector_code': ms['major_sector_code'],
                'sector_code': sector['sector_code'],
                'sector_name': sector['sector_name'],
                'sector_percent': sector.get('sector_percent')
            })

# insert major_sector_lookup
major_sector_lookup_df = pd.DataFrame(major_sector_rows).drop_duplicates(subset=['major_sector_code'])
major_sector_lookup_df.to_sql('major_sector_lookup', con=engine, if_exists='append', index=False)

# insert proj_sector_lookup
sector_lookup_df = pd.DataFrame(sector_rows)[['sector_code', 'sector_name']].drop_duplicates(subset=['sector_code'])
sector_lookup_df.to_sql('proj_sector_lookup', con=engine, if_exists='append', index=False)

# ── project_major_sectors junction ───────────────────
project_major_sectors_df = pd.DataFrame(major_sector_rows)[['project_id', 'major_sector_code']] if 'project_id' in major_sector_rows[0] else None

# we need project_id in major_sector_rows, so rebuild it:
pms_rows = []
ps_rows = []

for _, row in df.iterrows():
    proj_id = row['id']
    if not isinstance(row['major_sectors'], list):
        continue
    for ms_entry in row['major_sectors']:
        ms = ms_entry['major_sector']
        pms_rows.append({
            'project_id': proj_id,
            'major_sector_code': ms['major_sector_code']
        })
        for sector in ms.get('sectors', []):
            ps_rows.append({
                'project_id': proj_id,
                'major_sector_code': ms['major_sector_code'],
                'sector_code': sector['sector_code'],
                'sector_percent': sector.get('sector_percent')
            })

pms_df = pd.DataFrame(pms_rows)
pms_df.to_sql('project_major_sectors', con=engine, if_exists='append', index=False)

# now fetch back the auto-generated project_major_sector_ids so we can link project_sectors
pms_db = pd.read_sql('SELECT project_major_sector_id, project_id, major_sector_code FROM project_major_sectors', con=engine)

ps_df = pd.DataFrame(ps_rows)
ps_df = ps_df.merge(pms_db, on=['project_id', 'major_sector_code'], how='left')
ps_df = ps_df[['project_id', 'project_major_sector_id', 'sector_code', 'sector_percent']]
ps_df.to_sql('project_sectors', con=engine, if_exists='append', index=False)