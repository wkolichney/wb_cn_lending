"""
Pull IMF CDIS (Coordinated Direct Investment Survey) bilateral China FDI positions
from two independent sources for coverage comparison:

  Route 1 - DBnomics       (dataset IMF/CDIS)
  Route 2 - World Bank Data360 (dataset IMF_CDIS)

We pull two directions of the bilateral position (annual stocks, USD millions... see units note):
  - China-reported OUTWARD position to each counterpart   (REF_AREA=CN, indicator IOW)
  - Counterpart-reported INWARD position FROM China (MIRROR) (COUNTERPART=CN, indicator IIW)

Outputs (all in this folder):
  cdis_dbnomics_cn_outward.csv
  cdis_dbnomics_mirror_inward_from_cn.csv
  cdis_data360_cn_outward.csv
  cdis_data360_mirror_inward_from_cn.csv
"""
import requests, pandas as pd, time, sys

OUT = "."
DBN = "https://api.db.nomics.world/v22/series/IMF/CDIS"
D360 = "https://data360api.worldbank.org/data360/data"

# Total Direct Investment Position (all instruments), US Dollars
IND_OUT = "IOW_BP6_USD"   # Outward Direct Investment Positions, USD
IND_IN  = "IIW_BP6_USD"   # Inward  Direct Investment Positions, USD


# ---------------------------------------------------------------------------
# Route 1: DBnomics
# ---------------------------------------------------------------------------
def _dbnomics_codelists():
    """code->label maps for REF_AREA / COUNTERPART_AREA / INDICATOR."""
    r = requests.get("https://api.db.nomics.world/v22/datasets/IMF/CDIS", timeout=60)
    return r.json()["datasets"]["docs"][0]["dimensions_values_labels"]


def dbnomics_fetch(dimensions, label, codelists):
    """Page through the DBnomics series endpoint and return a tidy long DataFrame."""
    import json
    ra_cl = codelists["REF_AREA"]; cp_cl = codelists["COUNTERPART_AREA"]
    rows, offset = [], 0
    while True:
        params = {"dimensions": json.dumps(dimensions), "observations": "1",
                  "limit": 1000, "offset": offset}
        r = requests.get(DBN, params=params, timeout=120)
        r.raise_for_status()
        j = r.json()["series"]
        docs = j["docs"]
        for s in docs:
            dim = s.get("dimensions", {})
            ra = dim.get("REF_AREA"); cp = dim.get("COUNTERPART_AREA")
            per = s.get("period", []); val = s.get("value", [])
            for p, v in zip(per, val):
                rows.append({
                    "ref_area": ra, "ref_area_label": ra_cl.get(ra, ra),
                    "counterpart_area": cp, "counterpart_label": cp_cl.get(cp, cp),
                    "indicator": dim.get("INDICATOR"),
                    "year": p, "value_usd": v,
                })
        got = len(docs)
        offset += got
        print(f"  [dbnomics/{label}] fetched {offset}/{j['num_found']} series", file=sys.stderr)
        if offset >= j["num_found"] or got == 0:
            break
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df = df[pd.to_numeric(df["value_usd"], errors="coerce").notna()]
    return df


def run_dbnomics():
    cl = _dbnomics_codelists()
    out = dbnomics_fetch({"FREQ": ["A"], "REF_AREA": ["CN"], "INDICATOR": [IND_OUT]},
                         "cn_outward", cl)
    out.to_csv(f"{OUT}/cdis_dbnomics_cn_outward.csv", index=False)
    print(f"WROTE cdis_dbnomics_cn_outward.csv  rows={len(out)} "
          f"counterparts={out['counterpart_area'].nunique()} "
          f"years={out['year'].min()}-{out['year'].max()}")

    mir = dbnomics_fetch({"FREQ": ["A"], "COUNTERPART_AREA": ["CN"], "INDICATOR": [IND_IN]},
                         "mirror_inward", cl)
    mir.to_csv(f"{OUT}/cdis_dbnomics_mirror_inward_from_cn.csv", index=False)
    print(f"WROTE cdis_dbnomics_mirror_inward_from_cn.csv  rows={len(mir)} "
          f"reporters={mir['ref_area'].nunique()} "
          f"years={mir['year'].min()}-{mir['year'].max()}")


# ---------------------------------------------------------------------------
# Route 2: World Bank Data360
# ---------------------------------------------------------------------------
# Data360 quirks:
#   - all bilateral positions live under INDICATOR=IMF_CDIS_IW_BP6
#   - direction is in COMP_BREAKDOWN_2 (INV_DIR_OUT / INV_DIR_IN)
#   - counterpart economy is an OPAQUE code in COMP_BREAKDOWN_1 (IMF_CNT_COUNTRY_n)
#   - REF_AREA is ISO3; OBS_VALUE is raw USD (= DBnomics value * 1e6)
D360_IND = "IMF_CDIS_IW_BP6"


def data360_fetch(ref_area=None, counterpart_code=None, direction=None, label=""):
    rows, skip = [], 0
    while True:
        params = {"DATABASE_ID": "IMF_CDIS", "INDICATOR": D360_IND, "skip": skip, "top": 1000}
        if ref_area:        params["REF_AREA"] = ref_area
        if counterpart_code: params["COMP_BREAKDOWN_1"] = counterpart_code
        if direction:       params["COMP_BREAKDOWN_2"] = direction
        r = requests.get(D360, params=params, timeout=120)
        r.raise_for_status()
        j = r.json()
        batch = j.get("value", [])
        rows += batch
        skip += len(batch)
        print(f"  [data360/{label}] fetched {skip} (count={j.get('count')})", file=sys.stderr)
        if len(batch) == 0 or skip >= j.get("count", 0):
            break
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    if len(df):
        df["value_usd"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce") / 1e6  # -> millions USD
        df["year"] = pd.to_numeric(df["TIME_PERIOD"], errors="coerce").astype("Int64")
    return df


def _build_counterpart_decoder(d360_out, dbn_out_csv):
    """Map IMF_CNT_COUNTRY_n -> (iso2,label) by matching (year, rounded value) to DBnomics.

    A single (year,value) can collide across counterparts, so we vote across ALL of a
    code's year-value matches and keep the label only if it wins unambiguously.
    """
    from collections import Counter, defaultdict
    dbn = pd.read_csv(dbn_out_csv)
    key = lambda y, v: (int(y), round(float(v), 1))
    # a value in a given year may belong to several counterparts -> keep the set
    lookup = defaultdict(set)
    for r in dbn.itertuples():
        lookup[key(r.year, r.value_usd)].add((r.counterpart_area, r.counterpart_label))

    votes = defaultdict(Counter)
    for r in d360_out.itertuples():
        if pd.isna(r.value_usd) or pd.isna(r.year):
            continue
        cands = lookup.get(key(r.year, r.value_usd))
        if cands and len(cands) == 1:            # unambiguous year-value -> strong vote
            votes[r.COMP_BREAKDOWN_1][next(iter(cands))] += 1
    dec = {}
    for code, c in votes.items():
        (lab, n), = c.most_common(1)
        if n >= 1 and (len(c) == 1 or n > c.most_common(2)[1][1]):  # clear winner
            dec[code] = lab
    return dec


def run_data360():
    # China as reporter -> both directions, all years, all counterparts (coded)
    cn = data360_fetch(ref_area="CHN", label="china_reporter")
    out = cn[cn["COMP_BREAKDOWN_2"] == "INV_DIR_OUT"].copy()
    inw = cn[cn["COMP_BREAKDOWN_2"] == "INV_DIR_IN"].copy()

    # decode opaque counterpart codes using the clean DBnomics outward pull
    dec = _build_counterpart_decoder(out, f"{OUT}/cdis_dbnomics_cn_outward.csv")
    n_codes = out["COMP_BREAKDOWN_1"].nunique()
    print(f"  decoded {len(dec)}/{n_codes} counterpart codes via DBnomics value-match")
    out["counterpart_area"] = out["COMP_BREAKDOWN_1"].map(lambda c: dec.get(c, (None,))[0])
    out["counterpart_label"] = out["COMP_BREAKDOWN_1"].map(lambda c: dec.get(c, (None, None))[1])

    keep = ["REF_AREA", "counterpart_area", "counterpart_label", "COMP_BREAKDOWN_1",
            "year", "value_usd", "OBS_STATUS"]
    out[keep].sort_values(["counterpart_label", "year"]).to_csv(
        f"{OUT}/cdis_data360_cn_outward.csv", index=False)
    print(f"WROTE cdis_data360_cn_outward.csv  rows={len(out)} "
          f"counterparts={n_codes} years={int(out.year.min())}-{int(out.year.max())}")

    # find China's own counterpart code (needed for the mirror pull) from any reporter that
    # borders China in DBnomics mirror; reuse the outward decoder inverted is not possible,
    # so identify it from the US reporter's records matched to DBnomics mirror.
    dbn_mir = pd.read_csv(f"{OUT}/cdis_dbnomics_mirror_inward_from_cn.csv")
    us_mir = dbn_mir[dbn_mir.ref_area == "US"]
    us = data360_fetch(ref_area="USA", direction="INV_DIR_IN", label="us_inward")
    cn_code = None
    if len(us) and len(us_mir):
        km = {(int(r.year), round(float(r.value_usd), 1)): r.COMP_BREAKDOWN_1
              for r in us.itertuples() if pd.notna(r.value_usd) and pd.notna(r.year)}
        for r in us_mir.itertuples():
            c = km.get((int(r.year), round(float(r.value_usd), 1)))
            if c:
                cn_code = c
                break
    print(f"  China counterpart code = {cn_code}")

    if cn_code:
        mir = data360_fetch(counterpart_code=cn_code, direction="INV_DIR_IN", label="mirror_inward")
        mir = mir[["REF_AREA", "COMP_BREAKDOWN_1", "year", "value_usd", "OBS_STATUS"]]
        mir.sort_values(["REF_AREA", "year"]).to_csv(
            f"{OUT}/cdis_data360_mirror_inward_from_cn.csv", index=False)
        print(f"WROTE cdis_data360_mirror_inward_from_cn.csv  rows={len(mir)} "
              f"reporters={mir.REF_AREA.nunique()} years={int(mir.year.min())}-{int(mir.year.max())}")
    else:
        print("  SKIP mirror file: could not resolve China's counterpart code")


if __name__ == "__main__":
    print("=== Route 1: DBnomics ===")
    run_dbnomics()
    print("\n=== Route 2: World Bank Data360 ===")
    try:
        run_data360()
    except Exception as e:
        print("Data360 failed:", repr(e))
