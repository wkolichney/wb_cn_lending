"""
Quality check for the regression export (project_document_regression*.xlsx).

Every export column is rebuilt straight from the MySQL base tables with code that is
independent of main_regression_export.py (SQL aggregation + key lookups, no shared
helpers), then compared cell by cell, keyed on the World Bank project_id.

  1. export 3 vs export 4          -> qc_3_vs_4_projects.csv, qc_3_vs_4_cells.csv.gz
  2. export 3 vs base data         -> qc_base_mismatch_3.csv.gz
  3. export 4 vs base data         -> qc_base_mismatch_4.csv.gz
  4. integrity checks on export 4  -> qc_integrity_4.csv, qc_dtypes_4.csv
  5. project_major_sectors scope   -> qc_sector_duplicates.csv

Headline numbers for the report go to qc_summary.json.
Run from anywhere:  python sql_export/qc/export_qc.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

HERE = Path(__file__).resolve().parent
EXPORT_DIR = HERE.parent
OUT = HERE / 'output'
CACHE = OUT / 'cache'
CACHE.mkdir(parents=True, exist_ok=True)

DOC_TYPES = [
    'Project Information Document',
    'Procurement Plan',
    'Project Appraisal Document',
    'Implementation Status and Results Report',
    'Implementation Completion and Results Report',
]
DOC_PREFIXES = [t.replace(' ', '_').lower() for t in DOC_TYPES]
PROJECT_COLS = [
    'project_name', 'countryshortname', 'curr_ibrd_commitment', 'idacommamt',
    'totalamt', 'grantamt', 'lendprojectcost', 'boardapprovaldate', 'closingdate',
    'envassesmentcategorycode',
]
CONFLICT_COLS = ['num_conflicts', 'war', 'intrastate_conflict', 'conflict_active']
SECTOR_JOIN = """
    project_sectors ps
    JOIN project_major_sectors pms ON pms.project_major_sector_id = ps.project_major_sector_id
    JOIN major_sector_lookup   ms  ON ms.major_sector_code = pms.major_sector_code
    JOIN wb_condensed_sector   w   ON w.wb_condensed_sector_name = ms.wb_condensed_sector_name
"""


def q(sql):
    return pd.read_sql(sql, engine)


def load_export(n):
    """Read an export once; later runs use a pickle cache (re-read if the xlsx is newer)."""
    xlsx = EXPORT_DIR / f'project_document_regression{n}.xlsx'
    pkl = CACHE / f'{xlsx.stem}.pkl'
    if pkl.exists() and pkl.stat().st_mtime > xlsx.stat().st_mtime:
        return pd.read_pickle(pkl)
    df = pd.read_excel(xlsx)
    df.to_pickle(pkl)
    return df


def col_group(c):
    if c.startswith('sector_') or c == 'total_infra_pct':
        return 'sectors'
    if c.startswith(tuple(DOC_PREFIXES)):
        return 'documents'
    if c.startswith('china_steel'):
        return 'china steel'
    if c in PROJECT_COLS:
        return 'project attributes'
    if c in ('project_id', 'iso3', 'approval_year'):
        return 'keys'
    return 'country-year controls'


# ── base-level rebuild ──────────────────────────────────────────────────────
def build_expected():
    """Return (expected wide frame, expected sector lists, expected document candidates)."""
    types = ', '.join(f"'{t}'" for t in DOC_TYPES)

    # Universe: approved after 2000, >=1 document of the five types, >=1 full sector chain.
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
    keys = base[['project_id', 'iso3', 'approval_year']]

    # Country-year controls: aggregate in SQL to one row per (iso3, year), then look up.
    sources = {
        # these source columns are single-precision FLOAT; CAST keeps AVG at the stored precision
        'un': """SELECT iso3, year,
                   CAST(AVG(CASE WHEN us_china='CHN' THEN agree END) AS FLOAT) AS agree_chn,
                   CAST(AVG(CASE WHEN us_china='USA' THEN agree END) AS FLOAT) AS agree_usa,
                   CAST(AVG(CASE WHEN us_china='CHN' THEN ideal_point_distance END) AS FLOAT) AS ideal_point_distance_chn,
                   CAST(AVG(CASE WHEN us_china='USA' THEN ideal_point_distance END) AS FLOAT) AS ideal_point_distance_usa
                 FROM un_cn_agree GROUP BY iso3, year""",
        'trade': """SELECT iso3, year, MAX(exports) AS china_exports, MAX(`gdp$2015`) AS gdp_2015usd,
                      MAX(`export%%gdp`) AS china_export_pct_gdp FROM trade_china GROUP BY iso3, year""",
        'taiwan': 'SELECT iso3, year, MAX(taiwanrecognition) AS taiwanrecognition FROM taiwan_recognition GROUP BY iso3, year',
        'oil': """SELECT iso3, year, MAX(oil_prod) AS oil_prod, MAX(oil_value) AS oil_value,
                    MAX(gas_prod) AS gas_prod, MAX(gas_value) AS gas_value FROM oil_gas GROUP BY iso3, year""",
        'dac': 'SELECT iso3, year, SUM(value) AS dac_oda_received FROM dac_oda GROUP BY iso3, year',
        'fdi': 'SELECT iso3, year, MAX(flow) AS china_fdi_flow FROM bilateral_fdi GROUP BY iso3, year',
        'dsa': """SELECT dc.iso3, dc.year, MAX(dc.dsa) AS dsa, MAX(cl.s_p) AS sp_rating
                  FROM dsa_credit dc LEFT JOIN credit_lookup cl ON cl.credit_id = dc.credit_id
                  GROUP BY dc.iso3, dc.year""",
        'conflict': """SELECT iso3, year, COUNT(*) AS num_conflicts,
                         MAX(intensity_level = 2) AS war, MAX(type_of_conflict IN (3, 4)) AS intrastate_conflict
                       FROM ucdp_conflict GROUP BY iso3, year""",
        'polity': 'SELECT iso3, year, MAX(polity2) AS polity2 FROM democracy GROUP BY iso3, year',
        'vdem': 'SELECT iso3, year, MAX(v2x_pubcorr) AS v2x_pubcorr FROM corruption GROUP BY iso3, year',
    }
    exp = base.copy()
    wb = q('SELECT iso3, year, indicator_code, CAST(AVG(value) AS FLOAT) AS v FROM wb_indicator_pull GROUP BY 1, 2, 3')
    wb = wb.pivot(index=['iso3', 'year'], columns='indicator_code', values='v').reset_index()
    wb.columns.name = None
    for frame in [wb] + [q(s) for s in sources.values()]:
        frame = frame.rename(columns={'year': 'approval_year'})
        exp = exp.merge(frame, on=['iso3', 'approval_year'], how='left', validate='many_to_one')
    for c in CONFLICT_COLS[:3]:
        exp[c] = exp[c].fillna(0)  # UCDP lists active conflict-years only
    exp['conflict_active'] = (exp['num_conflicts'] > 0).astype(int)

    steel = q('SELECT year, china_steel FROM china_steel WHERE year >= 2000')
    for yr, v in zip(steel['year'], steel['china_steel']):
        exp[f'china_steel{yr}'] = v

    # Sectors as stored in the base tables, one entry per major sector code.
    sec = q(f"""
        SELECT ps.project_id, ms.major_sector_code, ms.major_sector_name,
               SUM(ps.sector_percent) AS pct, w.infrastructure AS infra
        FROM {SECTOR_JOIN}
        GROUP BY ps.project_id, ms.major_sector_code, ms.major_sector_name, w.infrastructure
    """)
    sec = sec[sec['project_id'].isin(base['project_id'])]
    sec['pct'] = sec['pct'].astype(float)
    sectors = {
        pid: sorted(zip(-g['pct'], g['major_sector_name'], g['infra']))
        for pid, g in sec.groupby('project_id')
    }
    infra = sec[sec['infra'] == 1].groupby('project_id')['pct'].sum()
    exp['total_infra_pct'] = exp['project_id'].map(infra).fillna(0)

    docs = q(f"""
        SELECT project_id, document_type, document_id, document_name, docdt
        FROM documents WHERE document_type IN ({types})
    """)
    docs = docs[docs['project_id'].isin(base['project_id'])]
    docs['docdt'] = pd.to_datetime(docs['docdt'])
    return exp, sectors, docs


# ── comparison ──────────────────────────────────────────────────────────────
def compare_cells(export, expected, cols):
    """Long frame of every non-matching cell: export value vs base-data value."""
    e = export.set_index('project_id')
    x = expected.set_index('project_id').reindex(e.index)
    out = []
    for c in cols:
        a, b = e[c], x[c]
        an, bn = a.isna().to_numpy(), b.isna().to_numpy()
        if c in ('boardapprovaldate', 'closingdate'):
            eq = (pd.to_datetime(a).dt.normalize() == pd.to_datetime(b).dt.normalize()).to_numpy()
        elif pd.api.types.is_numeric_dtype(b) or pd.api.types.is_numeric_dtype(a):
            av, bv = pd.to_numeric(a, errors='coerce'), pd.to_numeric(b, errors='coerce')
            eq = np.isclose(av, bv, rtol=1e-6, atol=1e-6)
        else:
            eq = (a.astype(str).str.strip() == b.astype(str).str.strip()).to_numpy()
        issue = np.select(
            [an & bn, ~an & bn, an & ~bn, eq],
            ['match', 'filled_should_be_NA', 'missing_should_have_value', 'match'],
            'wrong_value')
        bad = issue != 'match'
        if bad.any():
            out.append(pd.DataFrame({
                'project_id': e.index[bad], 'column': c, 'group': col_group(c),
                'export_value': a[bad].astype(str).to_numpy(),
                'base_value': b[bad].astype(str).to_numpy(), 'issue': issue[bad]}))
    return out


def compare_sectors(export, sectors, max_k):
    """Sector slots: same multiset of (pct, name, infra) as the base, nothing extra."""
    out = []
    e = export.set_index('project_id')
    for pid, row in e.iterrows():
        want = sectors.get(pid, [])
        n = len(want)
        for k in range(n + 1, max_k + 1):
            for f in ('name', 'pct', 'is_infra'):
                v = row[f'sector_{k}_{f}']
                if pd.notna(v):
                    out.append((pid, f'sector_{k}_{f}', 'sectors', str(v), 'nan', 'filled_should_be_NA'))
        have = []
        for k in range(1, n + 1):
            p, nm, inf = row[f'sector_{k}_pct'], row[f'sector_{k}_name'], row[f'sector_{k}_is_infra']
            if pd.isna(p):
                out.append((pid, f'sector_{k}_pct', 'sectors', 'nan', str(-want[k - 1][0]), 'missing_should_have_value'))
            else:
                have.append((-float(p), nm, int(inf)))
        got = sorted(have)
        if len(got) == n and any(abs(g[0] - w[0]) > 1e-6 or g[1] != w[1] or g[2] != w[2] for g, w in zip(got, want)):
            out.append((pid, f'sector_1..{n}', 'sectors', str([(-g[0], g[1]) for g in got]),
                        str([(-w[0], w[1]) for w in want]), 'wrong_value'))
    return pd.DataFrame(out, columns=['project_id', 'column', 'group', 'export_value', 'base_value', 'issue'])


def compare_documents(export, docs):
    """First/last document per type: id must be a document of that type dated on the
    earliest/latest date; name and date must belong to that same document."""
    by_id = docs.set_index('document_id')
    groups = {key: g for key, g in docs.groupby(['project_id', 'document_type'])}
    out = []
    e = export.set_index('project_id')
    for dtype_, prefix in zip(DOC_TYPES, DOC_PREFIXES):
        for pid, row in e.iterrows():
            g = groups.get((pid, dtype_))
            for end in ('first', 'last'):
                cid, cname, cdate = (f'{prefix}_{end}_{f}' for f in ('id', 'name', 'date'))
                vid, vname, vdate = row[cid], row[cname], row[cdate]
                if g is None:
                    for c, v in ((cid, vid), (cname, vname), (cdate, vdate)):
                        if pd.notna(v):
                            out.append((pid, c, 'documents', str(v), 'nan', 'filled_should_be_NA'))
                    continue
                dated = g['docdt'].dropna()
                target = (dated.min() if end == 'first' else dated.max()) if len(dated) else pd.NaT
                ok_ids = set(g.loc[g['docdt'] == target, 'document_id']) if pd.notna(target) else set(g['document_id'])
                if pd.isna(vid):
                    out.append((pid, cid, 'documents', 'nan', str(sorted(ok_ids)), 'missing_should_have_value'))
                    continue
                if int(vid) not in ok_ids:
                    out.append((pid, cid, 'documents', str(int(vid)), str(sorted(ok_ids)), 'wrong_value'))
                exp_date = target
                if not (pd.isna(vdate) and pd.isna(exp_date)) and pd.to_datetime(vdate) != exp_date:
                    out.append((pid, cdate, 'documents', str(vdate), str(exp_date), 'wrong_value'))
                if int(vid) in by_id.index:
                    exp_name = by_id.loc[int(vid), 'document_name']
                    if not (pd.isna(vname) and pd.isna(exp_name)) and str(vname).strip() != str(exp_name).strip():
                        out.append((pid, cname, 'documents', str(vname)[:80], str(exp_name)[:80], 'wrong_value'))
    return pd.DataFrame(out, columns=['project_id', 'column', 'group', 'export_value', 'base_value', 'issue'])


def base_check(export, expected, sectors, docs, label):
    """Steps 2 and 3: every export cell vs the base-data rebuild."""
    ids_exp, ids_out = set(expected['project_id']), set(export['project_id'])
    plain = [c for c in export.columns
             if col_group(c) not in ('sectors', 'documents') and c != 'project_id' and c in expected.columns]
    plain.append('total_infra_pct')
    common = export[export['project_id'].isin(ids_exp)]
    max_k = max(int(c.split('_')[1]) for c in export.columns if c.startswith('sector_') and c.endswith('_pct'))
    parts = compare_cells(common, expected, plain)
    parts.append(compare_sectors(common, sectors, max_k))
    parts.append(compare_documents(common, docs))
    mism = pd.concat(parts, ignore_index=True)
    meta = export.set_index('project_id')[['countryshortname', 'approval_year']]
    mism = mism.join(meta, on='project_id')
    mism.to_csv(OUT / f'qc_base_mismatch_{label}.csv.gz', index=False)

    checked_cells = len(common) * (len(export.columns) - 1)
    summary = {
        'rows': len(export), 'projects_missing_from_export': sorted(ids_exp - ids_out),
        'projects_not_in_base_universe': sorted(ids_out - ids_exp),
        'cells_checked': int(checked_cells), 'cells_mismatched': int(len(mism)),
        'projects_with_mismatch': int(mism['project_id'].nunique()),
        'by_issue': mism['issue'].value_counts().to_dict(),
        'by_group': mism.groupby(['group', 'issue']).size().unstack(fill_value=0).to_dict('index'),
        'by_column': mism['column'].value_counts().head(40).to_dict(),
    }
    return mism, summary


# ── step 1: export 3 vs export 4 ────────────────────────────────────────────
def diff_3_vs_4(e3, e4):
    assert e3['project_id'].is_unique and e4['project_id'].is_unique
    e4 = e4.set_index('project_id').reindex(e3['project_id']).reset_index()  # export-3 row order
    cols = [c for c in e3.columns if c in e4.columns and c != 'project_id']
    n = len(e3)
    cells = []
    for c in cols:
        a, b = e3[c], e4[c]
        an, bn = a.isna().to_numpy(), b.isna().to_numpy()
        only3 = ~an & bn
        only4 = an & ~bn
        if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
            differ = ~an & ~bn & ~np.isclose(a.astype(float), b.astype(float), rtol=1e-9)
        else:
            differ = ~an & ~bn & (a.astype(str).to_numpy() != b.astype(str).to_numpy())
        idx = np.flatnonzero(only3 | only4 | differ)
        if not len(idx):
            continue
        # donor = nearest row above (export-3 order) with a real value: what ffill copied
        pos = pd.Series(np.where(~bn, np.arange(n), np.nan)).ffill().shift(1).to_numpy()
        donor = pos[idx]
        cells.append(pd.DataFrame({
            'project_id': e3['project_id'].to_numpy()[idx],
            'countryshortname': e3['countryshortname'].to_numpy()[idx],
            'iso3': e4['iso3'].to_numpy()[idx],
            'approval_year': e3['approval_year'].to_numpy()[idx],
            'column': c, 'group': col_group(c),
            'value_in_3': a.to_numpy()[idx], 'value_in_4': b.to_numpy()[idx],
            'change': np.select([only3[idx], only4[idx]], ['filled_in_3_only', 'present_in_4_only'], 'value_differs'),
            'donor_row': donor,
        }))
    cells = pd.concat(cells, ignore_index=True)
    has_donor = cells['donor_row'].notna()
    d = cells.loc[has_donor, 'donor_row'].astype(int).to_numpy()
    cells['donor_project_id'] = pd.Series(dtype=str)
    cells.loc[has_donor, 'donor_project_id'] = e3['project_id'].to_numpy()[d]
    cells.loc[has_donor, 'donor_country'] = e3['countryshortname'].to_numpy()[d]
    cells['donor_same_country'] = cells['donor_country'] == cells['countryshortname']
    # sanity: the value in export 3 should equal what the donor row holds in export 4
    filled = cells['change'] == 'filled_in_3_only'
    donor_vals = [e4.at[int(r), c] for r, c in zip(cells.loc[filled, 'donor_row'], cells.loc[filled, 'column'])]
    same = [str(x) == str(y) or (isinstance(x, (int, float)) and isinstance(y, (int, float)) and np.isclose(x, y))
            for x, y in zip(cells.loc[filled, 'value_in_3'], donor_vals)]
    cells = cells.drop(columns='donor_row')
    cells.to_csv(OUT / 'qc_3_vs_4_cells.csv.gz', index=False)

    # per-project list (the main "problem rows" table)
    f = cells[cells['change'] == 'filled_in_3_only']
    per = f.pivot_table(index='project_id', columns='group', values='column', aggfunc='count', fill_value=0)
    per.columns = [f'cells_filled_{g.replace(" ", "_").replace("-", "_")}' for g in per.columns]
    per['cells_filled_total'] = per.sum(axis=1)
    ctrl = f[f['group'] == 'country-year controls'].groupby('project_id')['column'].agg(lambda s: ';'.join(s))
    per['controls_filled'] = ctrl
    amt = f[f['column'].isin(['totalamt', 'curr_ibrd_commitment', 'idacommamt', 'grantamt', 'lendprojectcost'])]
    per['amounts_filled'] = amt.groupby('project_id')['column'].agg(lambda s: ';'.join(s))
    pct3 = [c for c in e3.columns if c.startswith('sector_') and c.endswith('_pct')]
    s3 = e3.set_index('project_id')[pct3].sum(axis=1)
    s4 = e4.set_index('project_id')[pct3].sum(axis=1)
    meta = e3.set_index('project_id')[['countryshortname', 'approval_year', 'totalamt']].rename(
        columns={'totalamt': 'totalamt_in_3'})
    meta['totalamt_in_4'] = e4.set_index('project_id')['totalamt']
    meta['sector_pct_sum_in_3'] = s3
    meta['sector_pct_sum_in_4'] = s4
    per = meta.join(per, how='right').reset_index().sort_values('cells_filled_total', ascending=False)
    per.to_csv(OUT / 'qc_3_vs_4_projects.csv', index=False)

    # chart data
    controls = [c for c in cols if col_group(c) == 'country-year controls' and c not in CONFLICT_COLS]
    na_cmp = pd.DataFrame({'na_in_3': e3[controls].isna().sum(), 'na_in_4': e4[controls].isna().sum()})
    na_cmp['filled'] = na_cmp['na_in_4'] - na_cmp['na_in_3']
    yr = pd.DataFrame({
        'totalamt_3': e3.groupby('approval_year')['totalamt'].sum() / 1e9,
        'totalamt_4': e4.groupby('approval_year')['totalamt'].sum() / 1e9,
        'projects': e3.groupby('approval_year').size(),
    })
    filled_by_year = f.groupby('approval_year').size()
    yr['share_cells_filled'] = filled_by_year / (yr['projects'] * len(cols))
    bins = [0, 99.5, 100.5, 125, 150, 175, 200, 1000]
    labels = ['<100', '100', '101–125', '126–150', '151–175', '176–200', '>200']
    hist = pd.DataFrame({
        'export_3': pd.cut(s3, bins, labels=labels, include_lowest=True).value_counts().reindex(labels),
        'export_4': pd.cut(s4, bins, labels=labels, include_lowest=True).value_counts().reindex(labels),
    }).fillna(0).astype(int)
    by_group = f.groupby('group').agg(cells=('column', 'size'), projects=('project_id', 'nunique'))
    fab = f[f['column'] == 'totalamt']
    return {
        'cells_compared': int(n * len(cols)),
        'cells_changed': int(len(cells)),
        'by_change': cells['change'].value_counts().to_dict(),
        'projects_affected': int(f['project_id'].nunique()),
        'columns_affected': int(f['column'].nunique()),
        'donor_same_country_share': float(cells.loc[filled, 'donor_same_country'].mean()),
        'donor_value_verified_share': float(np.mean(same)) if same else None,
        'fabricated_totalamt_projects': int(len(fab)),
        'fabricated_totalamt_usd_bn': float(pd.to_numeric(fab['value_in_3']).sum() / 1e9),
        'by_group': by_group.to_dict('index'),
        'controls_na': na_cmp.sort_values('na_in_4', ascending=False).to_dict('index'),
        'by_year': yr.reset_index().to_dict('records'),
        'sector_sum_hist': hist.reset_index().rename(columns={'index': 'bin'}).to_dict('records'),
        'example_filled': f[f['column'] == 'polity2'].head(8)[
            ['project_id', 'countryshortname', 'approval_year', 'value_in_3', 'donor_project_id', 'donor_country']
        ].to_dict('records'),
    }


# ── step 4: integrity checks on one export ──────────────────────────────────
def expected_kind(c):
    if c in ('boardapprovaldate', 'closingdate') or c.endswith('_date'):
        return 'datetime'
    if c.endswith('_id') and c != 'project_id':
        return 'integer id'
    if c in ('project_id', 'project_name', 'countryshortname', 'envassesmentcategorycode', 'iso3',
             'dsa', 'sp_rating') or c.endswith('_name'):
        return 'string'
    if c.endswith('_is_infra') or c in ('taiwanrecognition', 'war', 'intrastate_conflict', 'conflict_active'):
        return '0/1'
    if c in ('approval_year', 'num_conflicts'):
        return 'integer'
    return 'number'


def dtype_report(df):
    rows = []
    for c in df.columns:
        kind, s = expected_kind(c), df[c]
        nn = s.dropna()
        if kind == 'datetime':
            ok, note = pd.api.types.is_datetime64_any_dtype(s), ''
        elif kind == 'string':
            ok, note = pd.api.types.is_string_dtype(s) or s.dtype == object, ''
        elif kind == 'integer id':
            whole = bool((nn % 1 == 0).all()) if pd.api.types.is_numeric_dtype(s) else False
            ok = pd.api.types.is_integer_dtype(s)
            note = 'stored as float because of NAs; values are whole numbers' if whole and not ok else ''
        elif kind == '0/1':
            vals = set(pd.to_numeric(nn, errors='coerce').unique())
            ok = vals <= {0, 1}
            note = '' if pd.api.types.is_integer_dtype(s) else 'float because of NAs'
        elif kind == 'integer':
            ok, note = pd.api.types.is_integer_dtype(s), ''
        else:
            ok = pd.api.types.is_numeric_dtype(s)
            note = 'whole numbers read back as int64 from Excel' if pd.api.types.is_integer_dtype(s) else ''
        status = 'fail' if not ok else ('warn' if note else 'pass')
        rows.append({'column': c, 'group': col_group(c), 'dtype': str(s.dtype), 'expected': kind,
                     'non_null': int(s.notna().sum()), 'status': status, 'note': note})
    return pd.DataFrame(rows)


def integrity_checks(df, base_summary):
    """Rule checks. Each rule: (name, category, boolean Series of failing rows, note)."""
    num = lambda c: pd.to_numeric(df[c], errors='coerce')
    pct = [c for c in df.columns if c.startswith('sector_') and c.endswith('_pct')]
    ssum = df[pct].sum(axis=1)
    rules = [
        ('project_id is unique', 'identity', df['project_id'].duplicated(keep=False), ''),
        ('project_id looks like a World Bank ID (P + 6 digits)', 'identity',
         ~df['project_id'].astype(str).str.fullmatch(r'P\d{6}'), ''),
        ('project_id not missing', 'identity', df['project_id'].isna(), ''),
        ('iso3 is a 3-letter code', 'identity', ~df['iso3'].astype(str).str.fullmatch(r'[A-Z]{3}'), ''),
        ('iso3 is a country, not a region/world aggregate', 'identity',
         df['iso3'].isin(['AFW', 'AFE', 'WLD', 'LCN', 'CSS', 'ECS', 'PSS', 'SAS', 'EAS', 'MEA', 'SSF', 'OED', 'ARB']),
         'regional projects cannot carry country-year controls'),
        ('approval_year = year of boardapprovaldate', 'consistency',
         df['approval_year'] != pd.to_datetime(df['boardapprovaldate']).dt.year, ''),
        ('boardapprovaldate after 2000-01-01', 'consistency', pd.to_datetime(df['boardapprovaldate']) <= '2000-01-01', ''),
        ('closingdate on/after boardapprovaldate', 'consistency',
         pd.to_datetime(df['closingdate']) < pd.to_datetime(df['boardapprovaldate']), ''),
        ('totalamt = IBRD + IDA commitment', 'amounts',
         (num('totalamt') - num('curr_ibrd_commitment').fillna(0) - num('idacommamt').fillna(0)).abs() > 1, ''),
        ('amounts are non-negative', 'amounts',
         (df[['curr_ibrd_commitment', 'idacommamt', 'totalamt', 'grantamt', 'lendprojectcost']] < 0).any(axis=1), ''),
        ('project cost ≤ 20× WB commitment', 'amounts',
         num('lendprojectcost') > 20 * num('totalamt').where(num('totalamt') > 0),
         'see amount_outliers: unit errors (P181649) and PforR program costs'),
        ('sector shares sum to 100', 'sectors', (ssum - 100).abs() > 0.5, 'see step 5: duplicate project_major_sectors'),
        ('each sector share within 0–100', 'sectors', ((df[pct] < 0) | (df[pct] > 100)).any(axis=1), ''),
        ('sectors ranked by share (descending)', 'sectors',
         (df[pct].diff(axis=1).iloc[:, 1:] > 1e-9).any(axis=1), ''),
        ('total_infra_pct ≤ 100', 'sectors', num('total_infra_pct') > 100.5, ''),
        ('environmental category is A/B/C/F/FI/U', 'project attributes',
         df['envassesmentcategorycode'].notna() & ~df['envassesmentcategorycode'].isin(['A', 'B', 'C', 'F', 'FI', 'U']), ''),
        ('polity2 within −10…10', 'controls', ~num('polity2').between(-10, 10) & df['polity2'].notna(), ''),
        ('v2x_pubcorr within 0…1', 'controls', ~num('v2x_pubcorr').between(0, 1) & df['v2x_pubcorr'].notna(), ''),
        ('UN agreement within 0…1', 'controls',
         (~num('agree_chn').between(0, 1) & df['agree_chn'].notna()) | (~num('agree_usa').between(0, 1) & df['agree_usa'].notna()), ''),
        ('taiwanrecognition is 0/1', 'controls', df['taiwanrecognition'].notna() & ~df['taiwanrecognition'].isin([0, 1]), ''),
        ('GDP and population positive', 'controls',
         (num('NY.GDP.MKTP.KD') <= 0) | (num('SP.POP.TOTL') <= 0), ''),
        ('gdp_2015usd = NY.GDP.MKTP.KD', 'controls',
         df['gdp_2015usd'].notna() & ~np.isclose(num('gdp_2015usd'), num('NY.GDP.MKTP.KD'), rtol=1e-5), ''),
        ('china_export_pct_gdp = exports / GDP × 100', 'controls',
         df['china_export_pct_gdp'].notna()
         & ~np.isclose(num('china_export_pct_gdp'), num('china_exports') / num('gdp_2015usd') * 100, rtol=1e-4), ''),
        ('conflict dummies consistent (war ⇒ active)', 'controls',
         (df['war'] > df['conflict_active']) | (df['intrastate_conflict'] > df['conflict_active']), ''),
        ('china_steel columns identical on every row', 'china steel',
         (df[[c for c in df.columns if c.startswith('china_steel')]].nunique() > 1).reindex(df.index, fill_value=False), ''),
    ]
    for prefix in DOC_PREFIXES:
        rules.append((f'{prefix}: first_date ≤ last_date', 'documents',
                      pd.to_datetime(df[f'{prefix}_first_date']) > pd.to_datetime(df[f'{prefix}_last_date']), ''))
    rows = []
    for name, cat, fail, note in rules:
        fail = fail.fillna(False).astype(bool)
        rows.append({'check': name, 'category': cat, 'rows_failing': int(fail.sum()), 'rows_checked': len(df),
                     'status': 'pass' if not fail.any() else 'fail',
                     'example_project_ids': ';'.join(df.loc[fail, 'project_id'].head(8)), 'note': note})
    rows.append({'check': 'every project in the base universe is exported', 'category': 'base data',
                 'rows_failing': len(base_summary['projects_missing_from_export']), 'rows_checked': len(df),
                 'status': 'pass' if not base_summary['projects_missing_from_export'] else 'fail',
                 'example_project_ids': ';'.join(base_summary['projects_missing_from_export'][:8]), 'note': ''})
    rows.append({'check': 'every cell matches the base-data rebuild', 'category': 'base data',
                 'rows_failing': base_summary['projects_with_mismatch'], 'rows_checked': len(df),
                 'status': 'pass' if base_summary['cells_mismatched'] == 0 else 'fail',
                 'example_project_ids': '', 'note': f"{base_summary['cells_mismatched']} cells; see qc_base_mismatch_4.csv.gz"})
    return pd.DataFrame(rows)


def source_duplicates():
    """(iso3, year) keys that appear more than once in a control table, and whether the copies disagree."""
    specs = {
        'taiwan_recognition': 'taiwanrecognition', 'oil_gas': 'oil_prod', 'democracy': 'polity2',
        'corruption': 'v2x_pubcorr', 'bilateral_fdi': 'flow', 'trade_china': 'exports',
        'dsa_credit': 'dsa', 'ucdp_conflict': None,
    }
    rows = []
    for t, v in specs.items():
        if v is None:
            continue
        d = q(f'SELECT iso3, year, COUNT(*) n, COUNT(DISTINCT {v}) nv FROM {t} GROUP BY iso3, year HAVING n > 1')
        rows.append({'table': t, 'duplicate_keys': len(d), 'keys_with_conflicting_values': int((d['nv'] > 1).sum())})
    d = q('SELECT iso3, year, indicator_code, COUNT(*) n, COUNT(DISTINCT value) nv FROM wb_indicator_pull '
          'GROUP BY 1, 2, 3 HAVING n > 1')
    rows.append({'table': 'wb_indicator_pull', 'duplicate_keys': len(d), 'keys_with_conflicting_values': int((d['nv'] > 1).sum())})
    d = q('SELECT iso3, year, us_china, COUNT(*) n, COUNT(DISTINCT agree) nv FROM un_cn_agree GROUP BY 1, 2, 3 HAVING n > 1')
    rows.append({'table': 'un_cn_agree', 'duplicate_keys': len(d), 'keys_with_conflicting_values': int((d['nv'] > 1).sum())})
    return rows


# ── step 5: project_major_sectors scope ─────────────────────────────────────
def sector_scope(universe_ids, e4):
    pms_dup = q("""SELECT project_id, major_sector_code, COUNT(*) AS n_rows
                   FROM project_major_sectors GROUP BY 1, 2 HAVING n_rows > 1""")
    ps = q(f"""SELECT ps.project_id, pms.major_sector_code, ps.sector_code, ps.sector_percent,
                      ps.project_major_sector_id, w.infrastructure AS infra
               FROM {SECTOR_JOIN}""")
    ps['sector_percent'] = ps['sector_percent'].astype(float)
    cur = ps.groupby(['project_id', 'major_sector_code'])['sector_percent'].sum()
    # dedupe: one row per (project, major sector, sub-sector) -- what the API actually lists
    dd = ps.drop_duplicates(['project_id', 'major_sector_code', 'sector_code'])
    fixed = dd.groupby(['project_id', 'major_sector_code'])['sector_percent'].sum()
    tbl = pd.DataFrame({'pct_now': cur, 'pct_deduped': fixed}).reset_index()
    tbl = tbl.merge(pms_dup, on=['project_id', 'major_sector_code'], how='inner')
    tbl['in_export'] = tbl['project_id'].isin(universe_ids)
    tbl.to_csv(OUT / 'qc_sector_duplicates.csv', index=False)

    tot_now = ps.groupby('project_id')['sector_percent'].sum()
    tot_fix = dd.groupby('project_id')['sector_percent'].sum()
    in_u = tot_fix.index.isin(universe_ids)
    infra_now = ps[ps['infra'] == 1].groupby('project_id')['sector_percent'].sum()
    infra_fix = dd[dd['infra'] == 1].groupby('project_id')['sector_percent'].sum()
    infra_chg = (infra_now.reindex(universe_ids).fillna(0) - infra_fix.reindex(universe_ids).fillna(0)).abs() > 0.5
    no_sector = q("""SELECT COUNT(*) n FROM projects p WHERE p.boardapprovaldate > '2000-01-01'
                     AND NOT EXISTS (SELECT 1 FROM project_sectors ps WHERE ps.project_id = p.project_id)""")['n'][0]
    pct = [c for c in e4.columns if c.startswith('sector_') and c.endswith('_pct')]
    over = e4.loc[(e4[pct].sum(axis=1) - 100).abs() > 0.5, 'project_id']
    return {
        'duplicate_pms_pairs': int(len(pms_dup)),
        'projects_with_duplicate_pms': int(pms_dup['project_id'].nunique()),
        'projects_with_duplicate_pms_in_export': int(
            pms_dup.loc[pms_dup['project_id'].isin(universe_ids), 'project_id'].nunique()),
        'export_projects_sum_not_100_now': int(((tot_now[tot_now.index.isin(universe_ids)] - 100).abs() > 0.5).sum()),
        'export_projects_sum_not_100_after_dedupe': int(((tot_fix[in_u] - 100).abs() > 0.5).sum()),
        'export_projects_off_100_after_dedupe': tot_fix[in_u][(tot_fix[in_u] - 100).abs() > 0.5].round(1).to_dict(),
        'export_projects_total_infra_pct_changes': int(infra_chg.sum()),
        'export4_rows_sum_not_100': int(len(over)),
        'export4_rows_sum_not_100_explained_by_duplicates': int(over.isin(pms_dup['project_id']).sum()),
        'post2000_projects_with_no_sector_rows': int(no_sector),
    }


def main():
    e3, e4 = load_export(3), load_export(4)
    expected, sectors, docs = build_expected()
    universe = set(expected['project_id'])

    s1 = diff_3_vs_4(e3, e4)
    _, s2 = base_check(e3, expected, sectors, docs, '3')
    _, s3 = base_check(e4, expected, sectors, docs, '4')

    dt = dtype_report(e4)
    dt.to_csv(OUT / 'qc_dtypes_4.csv', index=False)
    integ = integrity_checks(e4, s3)
    integ.to_csv(OUT / 'qc_integrity_4.csv', index=False)
    s5 = sector_scope(list(universe), e4)

    summary = {
        'step1_3_vs_4': s1, 'step2_base_vs_3': s2, 'step3_base_vs_4': s3,
        'step4_integrity': integ.to_dict('records'),
        'step4_dtypes': dt[dt['status'] != 'pass'].to_dict('records'),
        'step4_dtype_counts': dt['status'].value_counts().to_dict(),
        'step4_source_duplicates': source_duplicates(),
        'step5_sectors': s5,
    }
    (OUT / 'qc_summary.json').write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: v for k, v in summary.items() if k not in ('step4_integrity', 'step4_dtypes')},
                     indent=1, default=str)[:6000])


if __name__ == '__main__':
    main()
