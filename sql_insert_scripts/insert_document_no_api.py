import pandas as pd
import json
from sqlalchemy import create_engine
import sys
import re
sys.path.append('..')

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

def extract_nested(doc, field):
    val = doc.get(field)
    if isinstance(val, dict) and '0' in val:
        inner = val['0']
        if isinstance(inner, dict):
            return inner.get(list(inner.keys())[0])
    return val

# ── load from json ────────────────────────────────────
print("Loading all_documents_raw.json...")
with open('all_documents_raw.json', 'r') as f:
    all_documents = json.load(f)
print(f"Loaded {len(all_documents)} documents")

# ── build dataframe ───────────────────────────────────
rows = []
for doc_key, doc in all_documents.items():
    rows.append({
        'document_id':        doc.get('id'),
        'document_name':      extract_nested(doc, 'docna'),
        'document_type':      doc.get('docty'),
        'prdln':              doc.get('prdln'),
        'lndinstr':           extract_nested(doc, 'lndinstr'),
        'docdt':              doc.get('docdt'),
        'datestored':         doc.get('datestored'),
        'disclosure_date':    doc.get('disclosure_date'),
        'last_modified_date': doc.get('last_modified_date'),
        'pdfurl':             doc.get('pdfurl'),
        'txturl':             doc.get('txturl'),
        'url':                doc.get('url'),
        'maj_document_type':  doc.get('majdocty'),
        'disclstat':          doc.get('disclstat'),
        'versiontype':        doc.get('versiontyp'),
        'author':             extract_nested(doc, 'authors'),
        'security_class':     doc.get('seccl'),
        'lang':               doc.get('lang'),
        'repnb':              doc.get('repnb'),
        'volnb':              doc.get('volnb'),
        'display_title':      doc.get('display_title'),
        'chronical_docm_id':  doc.get('chronical_docm_id'),
        'guid':               doc.get('guid'),
        'owner':              doc.get('owner'),
        'project_id':         doc.get('projectid'),
    })

docs_df = pd.DataFrame(rows)

# ── clean dates ───────────────────────────────────────
for datecol in ['docdt', 'datestored', 'disclosure_date', 'last_modified_date']:
    docs_df[datecol] = pd.to_datetime(docs_df[datecol], errors='coerce').dt.date


# ── clean volumne number ───────────────────────────────────────
docs_df['volnb'] = pd.to_numeric(docs_df['volnb'], errors='coerce')

# ── filter to valid project_ids ───────────────────────
valid_projects = pd.read_sql('SELECT project_id FROM projects', con=engine)
valid_ids = set(valid_projects['project_id'])
docs_df = docs_df[docs_df['project_id'].isin(valid_ids)]
print(f"After FK filter: {len(docs_df)} documents")

# ── insert documents ──────────────────────────────────
docs_df.to_sql('documents', con=engine, if_exists='append', index=False)
print(f"Inserted {len(docs_df)} documents")

# ── build child table rows ────────────────────────────
doc_sector_rows = []
doc_theme_rows = []
doc_sub_sector_rows = []
doc_country_rows = []


for doc_key, doc in all_documents.items():
    doc_id = doc.get('id')
    if not doc_id:
        continue

    sectr = doc.get('sectr', {})
    if isinstance(sectr, dict):
        for entry in sectr.values():
            name = entry.get('sector', '').strip()
            if name:
                doc_sector_rows.append({'document_id': doc_id, 'sector_name': name})

    theme = doc.get('theme', '')
    if theme:
        for t in re.split(r',(?! )', theme):
            t = t.strip()
            if t:
                doc_theme_rows.append({'document_id': doc_id, 'theme_name': t})

    subsc = doc.get('subsc', '')
    if subsc:
        for s in re.split(r',(?! )', subsc):
            s = s.strip()
            if s:
                doc_sub_sector_rows.append({'document_id': doc_id, 'sub_sector_name': s})



# ── filter child rows to only inserted documents ──────
inserted_doc_ids = set(docs_df['document_id'].astype(str))

doc_sector_rows_filtered = [r for r in doc_sector_rows if r['document_id'] in inserted_doc_ids]
doc_theme_rows_filtered = [r for r in doc_theme_rows if r['document_id'] in inserted_doc_ids]
doc_sub_sector_rows_filtered = [r for r in doc_sub_sector_rows if r['document_id'] in inserted_doc_ids]

# ── insert doc_sector_lookup ──────────────────────────
doc_sector_lookup_df = pd.DataFrame(doc_sector_rows_filtered)[['sector_name']].drop_duplicates()
doc_sector_lookup_df.to_sql('doc_sector_lookup', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_sector_lookup_df)} doc_sector_lookup rows")

# ── insert doc_sector ─────────────────────────────────
doc_sector_df = pd.DataFrame(doc_sector_rows_filtered)
doc_sector_df.to_sql('doc_sector', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_sector_df)} doc_sector rows")

# ── insert doc_theme_lookup ───────────────────────────
doc_theme_lookup_df = pd.DataFrame(doc_theme_rows_filtered)[['theme_name']].drop_duplicates()
doc_theme_lookup_df.to_sql('doc_theme_lookup', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_theme_lookup_df)} doc_theme_lookup rows")

# ── insert doc_theme ──────────────────────────────────
doc_theme_df = pd.DataFrame(doc_theme_rows_filtered)
doc_theme_df.to_sql('doc_theme', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_theme_df)} doc_theme rows")

doc_sub_sector_lookup_df = pd.DataFrame(doc_sub_sector_rows)[['sub_sector_name']]
doc_sub_sector_lookup_df['sub_sector_name'] = doc_sub_sector_lookup_df['sub_sector_name'].str.strip().str.lower()
doc_sub_sector_lookup_df = doc_sub_sector_lookup_df.drop_duplicates()
# to sql
doc_sub_sector_lookup_df.to_sql('doc_sub_sector_lookup', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_sub_sector_lookup_df)} doc_sub_sector_lookup rows")

# ── insert doc_sub_sector ─────────────────────────────
doc_sub_sector_df = pd.DataFrame(doc_sub_sector_rows_filtered)
doc_sub_sector_df['sub_sector_name'] = doc_sub_sector_df['sub_sector_name'].str.strip().str.lower()
doc_sub_sector_df.to_sql('doc_sub_sector', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_sub_sector_df)} doc_sub_sector rows")

#  ── insert doc_country ─────────────────────────────
for doc_key, doc in all_documents.items():
    doc_id = doc.get('id')
    if not doc_id or doc_id not in inserted_doc_ids:
        continue
    
    count = doc.get('count', '')
    if count:
        for c in re.split(r',(?! )', str(count)):
            c = c.strip()
            if c:
                doc_country_rows.append({'document_id': doc_id, 'countryshortname': c})

# filter to only countries that exist in country table
valid_countries = set(pd.read_sql('SELECT countryshortname FROM country', con=engine)['countryshortname'])

doc_country_df = pd.DataFrame(doc_country_rows)
doc_country_df = doc_country_df[doc_country_df['countryshortname'].isin(valid_countries)]
doc_country_df.to_sql('doc_country', con=engine, if_exists='append', index=False)
print(f"Inserted {len(doc_country_df)} doc_country rows")