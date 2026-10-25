"""
Rebuild the regression dataset straight from the MySQL base tables.

This is the "base level" version of project_document_regression*.xlsx: same rows
(one per World Bank project_id) and same columns, but built without
main_regression_export.py, so its NULLs are the true missing values in the database.
null_analysis.py compares its nulls with export 3 and export 4.
"""
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

DOC_TYPES = [
    'Project Information Document',
    'Procurement Plan',
    'Project Appraisal Document',
    'Implementation Status and Results Report',
    'Implementation Completion and Results Report',
]
PROJECT_COLS = [
    'project_name', 'countryshortname', 'curr_ibrd_commitment', 'idacommamt', 'totalamt',
    'grantamt', 'lendprojectcost', 'boardapprovaldate', 'closingdate', 'envassesmentcategorycode',
]
SECTOR_JOIN = """
    project_sectors ps
    JOIN project_major_sectors pms ON pms.project_major_sector_id = ps.project_major_sector_id
    JOIN major_sector_lookup   ms  ON ms.major_sector_code = pms.major_sector_code
    JOIN wb_condensed_sector   w   ON w.wb_condensed_sector_name = ms.wb_condensed_sector_name
"""
# One SQL per country-year source, already collapsed to one row per (iso3, year).
CONTROL_SQL = [
    """SELECT iso3, year,
         AVG(CASE WHEN us_china='CHN' THEN agree END) AS agree_chn,
         AVG(CASE WHEN us_china='USA' THEN agree END) AS agree_usa,
         AVG(CASE WHEN us_china='CHN' THEN ideal_point_distance END) AS ideal_point_distance_chn,
         AVG(CASE WHEN us_china='USA' THEN ideal_point_distance END) AS ideal_point_distance_usa
       FROM un_cn_agree GROUP BY iso3, year""",
    """SELECT iso3, year, MAX(exports) AS china_exports, MAX(`gdp$2015`) AS gdp_2015usd,
         MAX(`export%%gdp`) AS china_export_pct_gdp FROM trade_china GROUP BY iso3, year""",
    'SELECT iso3, year, MAX(taiwanrecognition) AS taiwanrecognition FROM taiwan_recognition GROUP BY iso3, year',
    """SELECT iso3, year, MAX(oil_prod) AS oil_prod, MAX(oil_value) AS oil_value,
         MAX(gas_prod) AS gas_prod, MAX(gas_value) AS gas_value FROM oil_gas GROUP BY iso3, year""",
    'SELECT iso3, year, SUM(value) AS dac_oda_received FROM dac_oda GROUP BY iso3, year',
    'SELECT iso3, year, MAX(flow) AS china_fdi_flow FROM bilateral_fdi GROUP BY iso3, year',
    """SELECT dc.iso3, dc.year, MAX(dc.dsa) AS dsa, MAX(cl.s_p) AS sp_rating
       FROM dsa_credit dc LEFT JOIN credit_lookup cl ON cl.credit_id = dc.credit_id
       GROUP BY dc.iso3, dc.year""",
    """SELECT iso3, year, COUNT(*) AS num_conflicts, MAX(intensity_level = 2) AS war,
         MAX(type_of_conflict IN (3, 4)) AS intrastate_conflict FROM ucdp_conflict GROUP BY iso3, year""",
    'SELECT iso3, year, MAX(polity2) AS polity2 FROM democracy GROUP BY iso3, year',
    'SELECT iso3, year, MAX(v2x_pubcorr) AS v2x_pubcorr FROM corruption GROUP BY iso3, year',
]


def q(sql):
    return pd.read_sql(sql, engine)


def build_base():
    types = ', '.join(f"'{t}'" for t in DOC_TYPES)

    # 1. Projects in scope: approved after 2000, with >=1 document of the five types
    #    and >=1 complete sector chain (the export's inner joins).
    base = q(f"""
        SELECT p.project_id, {', '.join('p.' + c for c in PROJECT_COLS)}, c.iso3
        FROM projects p
        LEFT JOIN country c ON c.countryshortname = p.countryshortname
        WHERE p.boardapprovaldate > '2000-01-01'
          AND EXISTS (SELECT 1 FROM documents d
                      WHERE d.project_id = p.project_id AND d.document_type IN ({types}))
          AND EXISTS (SELECT 1 FROM {SECTOR_JOIN} WHERE ps.project_id = p.project_id)
    """)
    base['approval_year'] = pd.to_datetime(base['boardapprovaldate']).dt.year

    # 2. Sectors: one slot per major sector, largest share first.
    sec = q(f"""
        SELECT ps.project_id, ms.major_sector_name AS name, SUM(ps.sector_percent) AS pct,
               w.infrastructure AS is_infra
        FROM {SECTOR_JOIN}
        GROUP BY ps.project_id, ms.major_sector_code, ms.major_sector_name, w.infrastructure
    """)
    sec['pct'] = sec['pct'].astype(float)
    sec = sec.sort_values(['project_id', 'pct', 'name'], ascending=[True, False, True])
    sec['k'] = sec.groupby('project_id').cumcount() + 1
    slots = sec.pivot(index='project_id', columns='k', values=['name', 'pct', 'is_infra'])
    slots.columns = [f'sector_{k}_{field}' for field, k in slots.columns]
    base = base.merge(slots, left_on='project_id', right_index=True, how='left')
    infra = sec[sec['is_infra'] == 1].groupby('project_id')['pct'].sum()
    base['total_infra_pct'] = base['project_id'].map(infra).fillna(0)

    # 3. Documents: earliest and latest dated document of each type (lowest id on ties).
    docs = q(f"""
        SELECT project_id, document_type, document_id, document_name, docdt
        FROM documents WHERE document_type IN ({types})
    """)
    docs['docdt'] = pd.to_datetime(docs['docdt'])
    for dtype in DOC_TYPES:
        prefix = dtype.replace(' ', '_').lower()
        d = docs[docs['document_type'] == dtype]
        for end, ascending in (('first', True), ('last', False)):
            pick = (d.sort_values(['docdt', 'document_id'], ascending=[ascending, True], na_position='last')
                     .drop_duplicates('project_id')
                     .set_index('project_id'))
            base[f'{prefix}_{end}_id'] = base['project_id'].map(pick['document_id'])
            base[f'{prefix}_{end}_name'] = base['project_id'].map(pick['document_name'])
            base[f'{prefix}_{end}_date'] = base['project_id'].map(pick['docdt'])

    # 4. Country-year controls, matched on (iso3, approval year).
    wb = q('SELECT iso3, year, indicator_code, AVG(value) AS v FROM wb_indicator_pull GROUP BY 1, 2, 3')
    wb = wb.pivot(index=['iso3', 'year'], columns='indicator_code', values='v').reset_index()
    for frame in [wb] + [q(s) for s in CONTROL_SQL]:
        frame = frame.rename(columns={'year': 'approval_year'})
        base = base.merge(frame, on=['iso3', 'approval_year'], how='left', validate='many_to_one')
    for c in ['num_conflicts', 'war', 'intrastate_conflict']:
        base[c] = base[c].fillna(0)  # UCDP lists active conflict-years only: no row = no conflict
    base['conflict_active'] = (base['num_conflicts'] > 0).astype(int)

    # 5. China steel: one global series, the same on every row.
    steel = q('SELECT year, china_steel FROM china_steel WHERE year >= 2000')
    for yr, v in zip(steel['year'], steel['china_steel']):
        base[f'china_steel{yr}'] = v

    return base
