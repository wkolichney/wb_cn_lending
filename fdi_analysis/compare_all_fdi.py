"""
Compare ALL China-FDI sources head-to-head as China->destination-country panels.

Sources:
  A. BU greenfield        bu_asia_fdi.csv + bu_africa_fdi.csv  (project-level, greenfield)
  B. UNCTAD FdiFlowsStock US.FdiFlowsStock_*.csv               (China aggregate outward flows)
  C. CDIS outward (CN->X) cdis_dbnomics_cn_outward.csv          (positions, China self-reported)
  D. CDIS mirror  (X<-CN) cdis_dbnomics_mirror_inward_from_cn.csv (positions, host-reported)

Everything is keyed to ISO2 country + year so coverage can be compared on the same grid.
"""
import pandas as pd, numpy as np, re, pycountry

# ---------------- country -> ISO2 ----------------
OVERRIDE = {
    "Iran, Islamic Republic": "IR", "Korea, Dem. People's Rep.": "KP",
    "Korea, Rep.": "KR", "Kyrgyz Republic": "KG", "Lao People's Democratic Republic": "LA",
    "Russian Federation": "RU", "Syrian Arab Republic": "SY", "Taiwan, China": "TW",
    "Congo, Democratic Republic of the": "CD", "Congo, Republic of the": "CG",
    "Cote d'Ivoire": "CI", "Cabo Verde": "CV", "Vietnam": "VN", "Brunei": "BN",
    "Tanzania": "TZ", "Bolivia": "BO", "Venezuela": "VE", "Moldova": "MD",
}
def to_iso2(name):
    if not isinstance(name, str) or not name.strip():
        return None
    n = name.strip()
    # fix the Türkiye mojibake
    if n.startswith("T") and "rkiye" in n:
        return "TR"
    if n in OVERRIDE:
        return OVERRIDE[n]
    try:
        return pycountry.countries.lookup(n).alpha_2
    except LookupError:
        pass
    try:
        m = pycountry.countries.search_fuzzy(n)
        if m:
            return m[0].alpha_2
    except LookupError:
        return None
    return None

def is_real_iso2(code):
    if not isinstance(code, str) or len(code) != 2:
        return False
    try:
        pycountry.countries.lookup(code)
        return True
    except LookupError:
        return False

# ---------------- A. BU greenfield ----------------
def load_bu():
    asia = pd.read_csv("bu_asia_fdi.csv", header=1, low_memory=False)
    asia = asia[asia["Deal ID"].notna()]
    asia = asia.rename(columns={"Destination": "dest", "Year (Announced)": "yr",
                                "Amount - Announced (Million USD)": "amt"})
    afr = pd.read_csv("bu_africa_fdi.csv", low_memory=False)
    afr = afr.rename(columns={"Destination country": "dest", "Year (Announced)": "yr",
                              "Amount - Announced (Million USD)": "amt"})
    frames = []
    for d, reg in [(asia, "Asia"), (afr, "Africa")]:
        t = d[["dest", "yr", "amt", "Confidence Status"]].copy()
        t["region"] = reg
        frames.append(t)
    bu = pd.concat(frames, ignore_index=True)
    bu["iso2"] = bu["dest"].map(to_iso2)
    bu["yr"] = pd.to_numeric(bu["yr"], errors="coerce")
    bu["amt"] = pd.to_numeric(bu["amt"], errors="coerce")
    bu = bu[(bu.yr >= 2000) & (bu.yr <= 2025)]
    # drop projects flagged out
    bu_clean = bu[~bu["Confidence Status"].isin(["Duplicate", "Irrelevant"])]
    return bu, bu_clean

# ---------------- C/D. CDIS ----------------
def load_cdis():
    out = pd.read_csv("cdis_dbnomics_cn_outward.csv")
    out["iso2"] = out["counterpart_area"]
    out = out[out["iso2"].map(is_real_iso2)]
    mir = pd.read_csv("cdis_dbnomics_mirror_inward_from_cn.csv")
    mir["iso2"] = mir["ref_area"]
    mir = mir[mir["iso2"].map(is_real_iso2)]
    return out, mir

# ---------------- run ----------------
bu_all, bu = load_bu()
cdis_out, cdis_mir = load_cdis()

# universe of interest = BU destination countries
bu_univ = sorted(bu.dropna(subset=["iso2"]).iso2.unique())
print(f"BU destination countries mapped to ISO2: {len(bu_univ)} "
      f"(unmapped names: {sorted(set(bu_all[bu_all.iso2.isna()].dest.dropna()))})")

# per-source country-year panels
def panel(df, valcol):
    p = df.dropna(subset=["iso2"]).groupby(["iso2", df["yr" if "yr" in df else "year"]]) \
          if False else None
    return p

# build country-year coverage grids
def grid(df, yearcol, valcol):
    g = df.dropna(subset=["iso2", yearcol]).copy()
    g["has_val"] = pd.to_numeric(g[valcol], errors="coerce").notna()
    cell = g.groupby(["iso2", yearcol]).agg(n=("iso2", "size"), val=("has_val", "max")).reset_index()
    return cell

bu_cell   = grid(bu,       "yr",   "amt")
out_cell  = grid(cdis_out, "year", "value_usd")
mir_cell  = grid(cdis_mir, "year", "value_usd")

# ---- SOURCE-LEVEL SUMMARY ----
def summ(cell, name, yr):
    return {"source": name,
            "countries": cell.iso2.nunique(),
            "country_years": len(cell),
            "with_value": int(cell.val.sum()),
            "yr_min": int(cell[yr].min()), "yr_max": int(cell[yr].max())}
rows = [summ(bu_cell, "A. BU greenfield (deals)", "yr"),
        {"source": "B. UNCTAD FdiFlowsStock", "countries": 0, "country_years": 0,
         "with_value": 0, "yr_min": 2000, "yr_max": 2024},
        summ(out_cell, "C. CDIS outward CN->X", "year"),
        summ(mir_cell, "D. CDIS mirror X<-CN", "year")]
src_summary = pd.DataFrame(rows)
print("\n=== SOURCE-LEVEL COVERAGE ===")
print(src_summary.to_string(index=False))
src_summary.to_csv("fdi_source_comparison.csv", index=False)

# ---- COVERAGE OVER THE BU COUNTRY UNIVERSE ----
def covers(cell, iso, yr):
    return set(cell[cell.iso2 == iso][yr].tolist())
recs = []
for iso in bu_univ:
    try:
        name = pycountry.countries.lookup(iso).name
    except LookupError:
        name = iso
    bu_yrs = covers(bu_cell, iso, "yr")
    out_yrs = covers(out_cell, iso, "year")
    mir_yrs = covers(mir_cell, iso, "year")
    recs.append({"iso2": iso, "country": name,
                 "BU_years": len(bu_yrs), "BU_yr_range": f"{min(bu_yrs)}-{max(bu_yrs)}" if bu_yrs else "",
                 "CDISout_years": len(out_yrs), "CDISmir_years": len(mir_yrs),
                 "in_CDISmir": len(mir_yrs) > 0})
cov = pd.DataFrame(recs).sort_values("country")
cov.to_csv("fdi_country_coverage_matrix.csv", index=False)

print("\n=== BU COUNTRY UNIVERSE: how many covered by CDIS ===")
print(f"BU destination countries: {len(cov)}")
print(f"  also in CDIS mirror (X<-CN): {cov.in_CDISmir.sum()}")
print(f"  also in CDIS outward (CN->X): {(cov.CDISout_years>0).sum()}")
print(f"  NOT in CDIS mirror: {sorted(cov[~cov.in_CDISmir].country.tolist())}")
print("\nSample coverage matrix (first 15 rows):")
print(cov.head(15).to_string(index=False))
print("\nWrote: fdi_source_comparison.csv, fdi_country_coverage_matrix.csv")
