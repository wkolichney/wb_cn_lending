"""
Null analysis: base-level data vs regression export 3 vs regression export 4.

  base             nulls in the data rebuilt straight from MySQL (validation/base_data.py)
  base_as_reg3     the same base data put through export 3's frame-wide .ffill()
  reg3 / reg4      nulls in project_document_regression3.xlsx / ...4.xlsx

If export 4 is right, reg4 == base. If the ffill explanation is right, reg3 == base_as_reg3.
The gap base - reg3 is the number of cells export 3 filled with another project's value.

Run top to bottom (python validation/null_analysis.py) or cell by cell (# %%) in VS Code.
Charts and tables are saved to validation/output/.
"""
# %% setup
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from base_data import build_base

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / 'output'
OUT.mkdir(exist_ok=True)

COLORS = {'base': '#1baf7a', 'reg3': '#eb6834', 'reg4': '#2a78d6'}
sns.set_theme(style='whitegrid', rc={'axes.edgecolor': '#c3c2b7', 'grid.color': '#e1e0d9'})
pd.set_option('display.width', 200, 'display.max_rows', 200)


def show(df, title):
    """Print a table so it is readable in the terminal or the interactive window."""
    print(f'\n=== {title} ===')
    print(df.to_string())


def group_of(col):
    if col.startswith('sector_') or col == 'total_infra_pct':
        return 'sectors'
    if col.startswith(('project_information', 'procurement', 'project_appraisal', 'implementation_')):
        return 'documents'
    if col.startswith('china_steel'):
        return 'china steel'
    if col in ('project_name', 'countryshortname', 'curr_ibrd_commitment', 'idacommamt', 'totalamt',
               'grantamt', 'lendprojectcost', 'boardapprovaldate', 'closingdate',
               'envassesmentcategorycode', 'iso3', 'approval_year'):
        return 'project'
    return 'country-year controls'


# %% load base-level data and the two exports
reg3 = pd.read_excel(ROOT / 'sql_export' / 'project_document_regression3.xlsx')
reg4 = pd.read_excel(ROOT / 'sql_export' / 'project_document_regression4.xlsx')
base = build_base()

assert set(base['project_id']) == set(reg3['project_id']) == set(reg4['project_id']), 'project sets differ'
assert set(base.columns) == set(reg4.columns), set(base.columns) ^ set(reg4.columns)

# put every frame in export 3's row order (the order its ffill ran in) and column order
order = reg3['project_id']
base = base.set_index('project_id').loc[order].reset_index()[reg4.columns]
reg4 = reg4.set_index('project_id').loc[order].reset_index()

# %% null counts per variable
# Export 3's bug, applied to the base data: copy every value down into the blanks below it.
base_as_reg3 = base.ffill()

variables = [c for c in reg4.columns if c != 'project_id']
nulls = pd.DataFrame({
    'group': [group_of(c) for c in variables],
    'base': base[variables].isna().sum(),
    'base_as_reg3': base_as_reg3[variables].isna().sum(),
    'reg3': reg3[variables].isna().sum(),
    'reg4': reg4[variables].isna().sum(),
}, index=variables)
nulls['hidden_by_ffill'] = nulls['base'] - nulls['reg3']
nulls['reg4_matches_base'] = nulls['reg4'] == nulls['base']
nulls['reg3_matches_base_as_reg3'] = nulls['reg3'] == nulls['base_as_reg3']
nulls.index.name = 'variable'
nulls.to_csv(OUT / 'null_counts.csv')

# %% tables: where the null counts differ
show(nulls[nulls['hidden_by_ffill'] > 0].sort_values('hidden_by_ffill', ascending=False),
     'Variables whose nulls export 3 hid (base - reg3 > 0)')

summary = nulls.groupby('group')[['base', 'reg3', 'reg4', 'hidden_by_ffill']].sum()
summary['share_hidden'] = (summary['hidden_by_ffill'] / summary['base']).round(3)
show(summary, 'Null cells by group')

show(pd.DataFrame({
    'variables checked': [len(nulls)],
    'reg4 == base': [int(nulls['reg4_matches_base'].sum())],
    'reg3 == base put through ffill': [int(nulls['reg3_matches_base_as_reg3'].sum())],
}), 'Checks')


# %% chart 1: stacked bars -- each bar is the true null count (base = reg4),
# split into the nulls export 3 still showed and the nulls its ffill filled in.
def stacked_nulls(group):
    d = nulls[(nulls['group'] == group) & (nulls['base'] > 0)].sort_values('base', ascending=False)
    if d.empty:
        return
    fig, ax = plt.subplots(figsize=(max(8, 0.38 * len(d) + 2), 5.5))
    x = range(len(d))
    ax.bar(x, d['reg3'], width=0.7, color=COLORS['reg3'], edgecolor='white', linewidth=1,
           label='Still null in export 3')
    ax.bar(x, d['hidden_by_ffill'], bottom=d['reg3'], width=0.7, color=COLORS['reg4'],
           edgecolor='white', linewidth=1, label='Filled by ffill in export 3 (null in export 4)')
    ax.scatter(x, d['base'], marker='_', s=180, color='#0b0b0b', linewidths=2, zorder=3,
               label='Nulls in base data')
    ax.set_xticks(list(x), d.index, rotation=70, ha='right', fontsize=9)
    ax.set_ylabel('Number of nulls')
    ax.set_xlabel('')
    ax.set_title(f'Nulls per variable: {group} (out of {len(reg4):,} projects)', loc='left', fontsize=12)
    ax.legend(frameon=False, loc='upper right', fontsize=9)
    sns.despine(left=True)
    fig.tight_layout()
    fig.savefig(OUT / f'stacked_nulls_{group.replace(" ", "_").replace("-", "_")}.png', dpi=150)
    plt.show()


for g in ['country-year controls', 'project', 'sectors', 'documents']:
    stacked_nulls(g)


# %% chart 2: side-by-side bars -- base vs export 3 vs export 4 for every variable
def grouped_nulls(group):
    d = nulls[(nulls['group'] == group) & (nulls['base'] > 0)].sort_values('base', ascending=False)
    if d.empty:
        return
    long = (d[['base', 'reg3', 'reg4']].reset_index()
            .melt(id_vars='variable', var_name='dataset', value_name='nulls'))
    fig, ax = plt.subplots(figsize=(max(8, 0.55 * len(d) + 2), 5.5))
    sns.barplot(data=long, x='variable', y='nulls', hue='dataset', palette=COLORS,
                hue_order=['base', 'reg3', 'reg4'], saturation=1, edgecolor='white', linewidth=1, ax=ax)
    ax.tick_params(axis='x', rotation=70, labelsize=9)
    plt.setp(ax.get_xticklabels(), ha='right')
    ax.set_xlabel('')
    ax.set_ylabel('Number of nulls')
    ax.set_title(f'Nulls per variable: base data vs export 3 vs export 4 ({group})', loc='left', fontsize=12)
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles, ['Base data', 'Export 3', 'Export 4'], frameon=False, fontsize=9)
    sns.despine(left=True)
    fig.tight_layout()
    fig.savefig(OUT / f'grouped_nulls_{group.replace(" ", "_").replace("-", "_")}.png', dpi=150)
    plt.show()


for g in ['country-year controls', 'project', 'sectors', 'documents']:
    grouped_nulls(g)


# %% chart 3: the null-difference table drawn as a figure (country-year controls)
d = nulls[nulls['group'] == 'country-year controls'].sort_values('hidden_by_ffill', ascending=False)
d = d[d['base'] > 0][['base', 'reg3', 'reg4', 'hidden_by_ffill']]
fig, ax = plt.subplots(figsize=(8, 0.32 * len(d) + 1))
ax.axis('off')
tbl = ax.table(cellText=d.map(lambda v: f'{v:,}').to_numpy(), rowLabels=d.index,
               colLabels=['Base nulls', 'Export 3 nulls', 'Export 4 nulls', 'Hidden by ffill'],
               loc='center', cellLoc='right')
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.5)
tbl.scale(1, 1.25)
ax.set_title('Null counts, country-year controls', loc='left', fontsize=11)
fig.tight_layout()
fig.savefig(OUT / 'null_table_controls.png', dpi=150, bbox_inches='tight')
plt.show()
