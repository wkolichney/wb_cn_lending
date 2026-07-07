from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# All raw source files live in one place at the repo root.
MANUAL_DIR = Path(__file__).resolve().parent.parent / 'manual_file_location'
iso2 = pd.read_csv(MANUAL_DIR / 'GCI Database-Countries.csv')

iso2 = iso2[['2-Code ISO', '3-Code ISO']]
iso2 = iso2.rename(columns= {
    '2-Code ISO': 'iso2',
    '3-Code ISO': 'iso3'
})

iso2["iso2"] = iso2["iso2"].where(iso2["iso2"].notna(), other=None)

with engine.connect() as conn:
    for _, row in iso2[["iso3", "iso2"]].iterrows():
        conn.execute(
            text("UPDATE country SET iso2 = :iso2 WHERE iso3 = :iso3"),
            {"iso2": row["iso2"], "iso3": row["iso3"]}
        )
    conn.commit()