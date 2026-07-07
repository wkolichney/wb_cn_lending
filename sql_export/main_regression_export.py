from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# Write the export next to this script regardless of the working directory.
OUTPUT_PATH = Path(__file__).resolve().parent / 'project_document_regression.xlsx'



# ── QUERY: get sector percentages at the project × major_sector level ──────
query = """
SELECT 
    p.project_id,
    p.project_name,
    p.countryshortname,
    p.curr_ibrd_commitment,
    p.idacommamt,
    p.totalamt,
    p.grantamt,
    p.lendprojectcost,
    p.boardapprovaldate,
    p.closingdate,
    p.envassesmentcategorycode,

    -- sector with percentage
    ms.major_sector_code,
    ms.major_sector_name,
    SUM(ps.sector_percent)   AS major_sector_pct,   -- roll up sub-sectors

    -- condensed sector
    wbs.wb_condensed_sector_name,
    wbs.infrastructure,

    -- documents
    d.document_id,
    d.document_name,
    d.document_type,
    d.docdt

FROM projects AS p

-- sector percentage chain
JOIN project_sectors          AS ps  ON  ps.project_id            = p.project_id
JOIN project_major_sectors    AS pms ON  pms.project_major_sector_id = ps.project_major_sector_id
JOIN major_sector_lookup      AS ms  ON  ms.major_sector_code      = pms.major_sector_code
JOIN wb_condensed_sector      AS wbs ON  wbs.wb_condensed_sector_name = ms.wb_condensed_sector_name

-- documents
JOIN documents AS d ON d.project_id = p.project_id

WHERE d.document_type IN (
    'Project Information Document',
    'Procurement Plan',
    'Project Appraisal Document',
    'Implementation Status and Results Report',
    'Implementation Completion and Results Report'
)
AND p.boardapprovaldate > '2000-01-01'

GROUP BY
    p.project_id, p.project_name, p.countryshortname,
    p.curr_ibrd_commitment, p.idacommamt, p.totalamt, p.grantamt,
    p.lendprojectcost, p.boardapprovaldate, p.closingdate,
    p.envassesmentcategorycode,
    ms.major_sector_code, ms.major_sector_name,
    wbs.wb_condensed_sector_name, wbs.infrastructure,
    d.document_id, d.document_name, d.document_type, d.docdt
;
"""
df = pd.read_sql(query, engine)


query = """ 
SELECT
    year,
    china_steel
FROM china_steel;
"""
steel_df = pd.read_sql(query, engine)



# ── STEP 1: project base ────────────────────────────────────────────────────
project_cols = [
    'project_id', 'project_name', 'countryshortname',
    'curr_ibrd_commitment', 'idacommamt', 'totalamt', 'grantamt',
    'lendprojectcost', 'boardapprovaldate', 'closingdate',
    'envassesmentcategorycode'
]
project_base = df[project_cols].drop_duplicates('project_id')

# ── STEP 2: sector wide — name + percentage columns ────────────────────────
# One row per project × major_sector (already grouped in SQL)
sector_df = (
    df[['project_id', 'major_sector_name', 'major_sector_pct',
        'wb_condensed_sector_name', 'infrastructure']]
    .drop_duplicates()
    .sort_values(['project_id', 'major_sector_pct'], ascending=[True, False])
)

# Rank sectors within each project by descending share
sector_df['sector_rank'] = (
    sector_df.groupby('project_id')['major_sector_pct']
    .rank(method='first', ascending=False).astype(int)
)

# Pivot: sector_1_name, sector_1_pct, sector_1_condensed ... up to N sectors
max_sectors = sector_df['sector_rank'].max()

sector_wide = project_base[['project_id']].copy()
for rank in range(1, max_sectors + 1):
    sub = sector_df[sector_df['sector_rank'] == rank][
        ['project_id', 'major_sector_name', 'major_sector_pct', 'infrastructure']
    ].rename(columns={
        'major_sector_name':       f'sector_{rank}_name',
        'major_sector_pct':        f'sector_{rank}_pct',
        'infrastructure':          f'sector_{rank}_is_infra',
    })
    sector_wide = sector_wide.merge(sub, on='project_id', how='left')

# Convenience: total infrastructure % across all sectors
infra_pct = (
    sector_df[sector_df['infrastructure'] == 1]
    .groupby('project_id')['major_sector_pct']
    .sum()
    .reset_index()
    .rename(columns={'major_sector_pct': 'total_infra_pct'})
)
sector_wide = sector_wide.merge(infra_pct, on='project_id', how='left')
sector_wide['total_infra_pct'] = sector_wide['total_infra_pct'].fillna(0)

# ── STEP 3: documents wide (first + last per type) ─────────────────────────
doc_fields = ['document_id', 'document_name', 'docdt']
doc_types  = df['document_type'].dropna().unique()

doc_wide = project_base[['project_id']].copy()

for doc_type in doc_types:
    col_prefix = doc_type.replace(' ', '_').replace('/', '_').lower()
    sorted_docs = (
        df[df['document_type'] == doc_type][['project_id'] + doc_fields]
        .drop_duplicates()
        .sort_values('docdt', ascending=True)
    )
    first_doc = (
        sorted_docs.groupby('project_id').first().reset_index()
        .rename(columns={
            'document_id':   f'{col_prefix}_first_id',
            'document_name': f'{col_prefix}_first_name',
            'docdt':         f'{col_prefix}_first_date',
        })
    )
    last_doc = (
        sorted_docs.groupby('project_id').last().reset_index()
        .rename(columns={
            'document_id':   f'{col_prefix}_last_id',
            'document_name': f'{col_prefix}_last_name',
            'docdt':         f'{col_prefix}_last_date',
        })
    )
    doc_wide = doc_wide.merge(first_doc, on='project_id', how='left')
    doc_wide = doc_wide.merge(last_doc,  on='project_id', how='left')

# ── STEP 4: combine ───────────────────────────────────────────────
final_df = (
    project_base
    .merge(sector_wide, on='project_id', how='left')
    .merge(doc_wide,    on='project_id', how='left')
)

# ── STEP 5: country-year control variables ─────────────────────────────────
# Attach iso3 (via the country lookup) and the project's board-approval year,
# then merge every (iso3, year) control onto the project at that year. These
# are added regression controls — they build on top of the existing
# project / sector / document columns and do not modify them.
iso_lookup = pd.read_sql(
    'SELECT countryshortname, iso3 FROM country WHERE iso3 IS NOT NULL', engine
)
final_df = final_df.merge(iso_lookup, on='countryshortname', how='left')
final_df['approval_year'] = pd.to_datetime(final_df['boardapprovaldate']).dt.year


def merge_control(base, ctrl):
    """Left-merge a (iso3, year) control frame onto the project at approval year."""
    return base.merge(
        ctrl.rename(columns={'year': 'approval_year'}),
        on=['iso3', 'approval_year'], how='left'
    )


# --- World Bank development + governance indicators (long -> wide) ----------
ind = pd.read_sql(
    'SELECT iso3, year, indicator_code, value FROM wb_indicator_pull', engine
)
ind_wide = (
    ind.pivot_table(index=['iso3', 'year'], columns='indicator_code',
                    values='value', aggfunc='mean')
    .reset_index()
)
ind_wide.columns.name = None
final_df = merge_control(final_df, ind_wide)

# --- UN voting agreement / ideal-point distance vs US and China ------------
un = pd.read_sql(
    'SELECT iso3, year, agree, ideal_point_distance, us_china FROM un_cn_agree', engine
)
un_wide = un.pivot_table(index=['iso3', 'year'],
                         columns='us_china',
                         values=['agree', 'ideal_point_distance'])
# flatten MultiIndex columns -> agree_usa, agree_chn, ideal_point_distance_usa, ...
un_wide.columns = [f'{metric}_{cp.lower()}' for metric, cp in un_wide.columns]
un_wide = un_wide.reset_index()
final_df = merge_control(final_df, un_wide)

# --- China exports / trade exposure ----------------------------------------
trade = pd.read_sql(
    # %% escapes the literal % so pymysql does not treat it as a parameter marker
    'SELECT iso3, year, exports, `gdp$2015`, `export%%gdp` FROM trade_china', engine
).rename(columns={
    'exports':    'china_exports',
    'gdp$2015':   'gdp_2015usd',
    'export%gdp': 'china_export_pct_gdp',
})
final_df = merge_control(final_df, trade)

# --- Taiwan diplomatic recognition -----------------------------------------
# GROUP BY collapses duplicate (iso3, year) rows to one (the table contains a
# full duplicate insert; values agree, so MAX is safe and avoids row fan-out).
taiwan = pd.read_sql(
    'SELECT iso3, year, MAX(taiwanrecognition) AS taiwanrecognition '
    'FROM taiwan_recognition GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, taiwan)

# --- Oil & gas production / value ------------------------------------------
# GROUP BY collapses duplicate (iso3, year) rows (e.g. SDN) to one per key.
oil_gas = pd.read_sql(
    'SELECT iso3, year, MAX(oil_prod) AS oil_prod, MAX(oil_value) AS oil_value, '
    'MAX(gas_prod) AS gas_prod, MAX(gas_value) AS gas_value '
    'FROM oil_gas GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, oil_gas)

# --- DAC ODA received (summed across all donors) ---------------------------
dac = pd.read_sql(
    'SELECT iso3, year, SUM(value) AS dac_oda_received '
    'FROM dac_oda GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, dac)

# --- Bilateral FDI from China to the country -------------------------------
# Now a country-year control (previously a global China-outflow series).
# GROUP BY guards against duplicate (iso3, year) rows fanning out the merge.
bilateral_fdi = pd.read_sql(
    'SELECT iso3, year, MAX(flow) AS china_fdi_flow '
    'FROM bilateral_fdi GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, bilateral_fdi)

# --- Debt sustainability analysis + sovereign credit rating ----------------
# dsa_credit -> credit_lookup; use the S&P (s_p) rating per the data spec.
# MAX dedupes any duplicate (iso3, year) rows (MAX on text returns one value).
dsa_credit = pd.read_sql(
    'SELECT dc.iso3, dc.year, MAX(dc.dsa) AS dsa, MAX(cl.s_p) AS sp_rating '
    'FROM dsa_credit AS dc '
    'LEFT JOIN credit_lookup AS cl ON cl.credit_id = dc.credit_id '
    'GROUP BY dc.iso3, dc.year', engine
)
final_df = merge_control(final_df, dsa_credit)

# --- UCDP/PRIO armed conflict presence (country-year) ----------------------
# ucdp_conflict has one row per conflict x year x location-country (iso3 attached
# at load). Collapse to one row per (iso3, year).
conflict = pd.read_sql(
    'SELECT iso3, year, '
    'COUNT(*) AS num_conflicts, '
    'MAX(CASE WHEN intensity_level = 2 THEN 1 ELSE 0 END) AS war, '
    'MAX(CASE WHEN type_of_conflict IN (3,4) THEN 1 ELSE 0 END) AS intrastate_conflict '
    'FROM ucdp_conflict GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, conflict)
# CRITICAL: UCDP only records *active* conflict-years. A non-match after the left
# merge means "no conflict that year" -> 0, NOT missing. (Unlike oil/fdi/dsa where
# NaN is genuinely unknown.)
for col in ['num_conflicts', 'war', 'intrastate_conflict']:
    final_df[col] = final_df[col].fillna(0).astype(int)
final_df['conflict_active'] = (final_df['num_conflicts'] > 0).astype(int)

# --- Polity2 democracy score (country-year) ---------------------------------
# Range -10 (full autocracy) to +10 (full democracy). GROUP BY guards against
# duplicate (iso3, year) rows fanning out the merge.
democracy = pd.read_sql(
    'SELECT iso3, year, MAX(polity2) AS polity2 '
    'FROM democracy GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, democracy)

# --- V-Dem public sector corruption index (country-year) -------------------
# v2x_pubcorr range 0-1, higher = more corrupt. GROUP BY guards against
# duplicate (iso3, year) rows fanning out the merge.
corruption = pd.read_sql(
    'SELECT iso3, year, MAX(v2x_pubcorr) AS v2x_pubcorr '
    'FROM corruption GROUP BY iso3, year', engine
)
final_df = merge_control(final_df, corruption)

# ── STEP 6: global year-series controls (wide, replicated onto every row) ───
# China steel has a year column but no country dimension, so it is pivoted wide
# (one column per year) and joined onto every project row. (China FDI is now a
# country-year bilateral control in STEP 5, not a global series.)
year_steel_df = steel_df[steel_df['year'] >= 2000]  # years we care about
wide_steel_df = year_steel_df.pivot_table(index=None, columns='year', values='china_steel')
wide_steel_df.columns = [f'china_steel{yr}' for yr in wide_steel_df.columns]
wide_steel_df = wide_steel_df.reset_index(drop=True)

# ── STEP 7: join global series and export ──────────────────────────────────
larger_df = final_df.reset_index(drop=True)
larger_df = larger_df.join(wide_steel_df).ffill()

# Export
larger_df.to_excel(OUTPUT_PATH, index=False)
print(f'Wrote {len(larger_df)} rows x {larger_df.shape[1]} cols -> {OUTPUT_PATH.name}')