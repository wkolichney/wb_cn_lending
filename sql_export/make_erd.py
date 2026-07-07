"""Render an ERD for wb_proj_doc from the live schema -> images/erd_schema.png"""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import pandas as pd
from sqlalchemy import create_engine

e = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')
fk = pd.read_sql("""SELECT table_name c, column_name col, referenced_table_name p
                    FROM information_schema.key_column_usage
                    WHERE table_schema='wb_proj_doc' AND referenced_table_name IS NOT NULL""", e)
fk.columns = fk.columns.str.lower()

GROUPS = {
    'hub':      ('#F4C430', '#8a6d00'),   # country
    'core':     ('#8FB8DE', '#204060'),   # projects/documents
    'sector':   ('#A8D5BA', '#20503a'),   # sector chain
    'docdet':   ('#C9B6E4', '#402060'),   # document detail
    'control':  ('#F2A6A6', '#602020'),   # country-year controls
    'lookup':   ('#D9D9D9', '#404040'),   # lookups / reference
    'standalone':('#F6C28B','#7a4a10'),
}

# (x, y, group, key-columns text).  x:0-24  y:0-16
N = {
 'country':            (10.4, 8.4, 'hub', 'countryshortname (PK)\niso3, iso2'),
 # --- project / document core ---
 'projects':           (3.5, 8.4, 'core', 'project_id (PK)\ncountryshortname (FK)'),
 'documents':          (3.5, 10.8,'core', 'document_id (PK)\nproject_id (FK)'),
 'borrower':           (0.2, 9.2, 'core', 'project_id (FK)'),
 'impagency':          (0.2, 7.6, 'core', 'project_id (FK)'),
 # --- sector chain ---
 'project_major_sectors':(5.8,6.5,'sector','project_id (FK)\nmajor_sector_code (FK)'),
 'project_sectors':    (3.0, 4.9, 'sector','project_id (FK)\nproject_major_sector_id (FK)\nsector_code (FK), sector_percent'),
 'major_sector_lookup':(6.5, 4.3, 'sector','major_sector_code (PK)\nwb_condensed_sector_name (FK)'),
 'proj_sector_lookup': (0.2, 4.6, 'lookup','sector_code (PK)'),
 'wb_condensed_sector':(7.8, 2.6, 'lookup','wb_condensed_sector_name (PK)\ninfrastructure'),
 # --- document detail ---
 'doc_country':        (7.6, 11.2,'docdet','document_id (FK)\ncountryshortname (FK)'),
 'doc_theme':          (0.2, 13.0,'docdet','document_id (FK)\ntheme_name (FK)'),
 'doc_sector':         (3.5, 13.0,'docdet','document_id (FK)\nsector_name (FK)'),
 'doc_sub_sector':     (0.2, 15.0,'docdet','document_id (FK)\nsub_sector_name (FK)'),
 'doc_theme_lookup':   (3.5, 15.0,'lookup','theme_name (PK)'),
 'doc_sector_lookup':  (6.8, 13.0,'lookup','sector_name (PK)'),
 'doc_sub_sector_lookup':(6.8,15.0,'lookup','sub_sector_name (PK)'),
 # --- country-year controls (all FK -> country.iso3) ---
 'country_alternate':  (13.6,13.0,'control','iso3 (FK)\ncountryshortname'),
 'wb_indicator_pull':  (13.6,15.0,'control','iso3 (FK), year\nindicator_code (FK), value'),
 'wb_indicators':      (17.4,15.0,'lookup','indicator_code (PK)'),
 'un_cn_agree':        (17.4,13.0,'control','iso3 (FK), year\nagree, ideal_point_distance'),
 'trade_china':        (20.8,13.0,'control','iso3 (FK), year\nexports, export%gdp'),
 'taiwan_recognition': (13.6,11.0,'control','iso3 (FK), year\ntaiwanrecognition'),
 'oil_gas':            (17.4,11.0,'control','iso3 (FK), year\noil/gas prod & value'),
 'dsa_credit':         (20.8,11.0,'control','iso3 (FK), year\ndsa, credit_id (FK)'),
 'credit_lookup':      (20.8,9.2, 'lookup','credit_id (PK)\ns_p, moody, fitch'),
 'democracy':          (13.6,9.2, 'control','iso3 (FK), year\npolity2'),
 'dac_oda':            (17.4,9.2, 'control','iso3 (FK), year\ndonor, value'),
 'corruption':         (13.6,7.4, 'control','iso3 (FK), year\nv2x_pubcorr'),
 'bilateral_fdi':      (17.4,7.4, 'control','iso3 (FK), year\nflow'),
 'ucdp_conflict':      (20.8,7.4, 'control','iso3 (FK), year\nintensity, type'),
 'china_steel':        (20.8,5.6, 'standalone','year (PK)\nchina_steel (joins by YEAR only)'),
}

BW, BH = 3.05, 1.55
fig, ax = plt.subplots(figsize=(24, 17))
ax.set_xlim(-0.5, 24.5); ax.set_ylim(2.2, 17.6); ax.axis('off')

def center(t): x, y, *_ = N[t]; return (x + BW/2, y + BH/2)

# edges first (behind boxes)
for r in fk.itertuples():
    if r.c in N and r.p in N:
        x0, y0 = center(r.c); x1, y1 = center(r.p)
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>',
                     mutation_scale=14, color='#9aa0a6', lw=1.0,
                     connectionstyle='arc3,rad=0.08', shrinkA=26, shrinkB=26, zorder=1))

for name, (x, y, g, cols) in N.items():
    fill, edge = GROUPS[g]
    ax.add_patch(FancyBboxPatch((x, y), BW, BH, boxstyle='round,pad=0.02,rounding_size=0.1',
                 fc=fill, ec=edge, lw=1.4, zorder=3))
    ax.text(x + BW/2, y + BH - 0.28, name, ha='center', va='top', fontsize=10.5,
            fontweight='bold', color=edge, zorder=4)
    ax.text(x + BW/2, y + BH - 0.62, cols, ha='center', va='top', fontsize=7.4,
            color='#222', zorder=4)

# legend
leg = [('country (hub)','hub'),('project / document core','core'),('sector chain','sector'),
       ('document detail','docdet'),('country-year controls','control'),
       ('lookup / reference','lookup'),('standalone (year only)','standalone')]
for i,(lab,g) in enumerate(leg):
    ax.add_patch(FancyBboxPatch((-0.3 + i*3.45, 17.05), 0.35, 0.30,
                 boxstyle='round,pad=0.01', fc=GROUPS[g][0], ec=GROUPS[g][1], zorder=4))
    ax.text(0.15 + i*3.45, 17.2, lab, fontsize=8.8, va='center', ha='left', color='#222')

ax.set_title('wb_proj_doc — Entity-Relationship Diagram   (arrows point child → parent; FK = foreign key, PK = primary key)',
             fontsize=15, fontweight='bold', pad=16)
plt.tight_layout()
out = Path(__file__).resolve().parent.parent / 'images' / 'erd_schema.png'
plt.savefig(out, dpi=110, bbox_inches='tight', facecolor='white')
print('wrote', out)
