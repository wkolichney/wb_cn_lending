"""   
https://projects.worldbank.org/en/projects-operations/project-sector

Use this sector for manually bridging WB's API sector to their webpage/dashboard version of their sectors
"""

import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine('mysql+pymysql://root:root@localhost/wb_proj_doc')

# This is based off my manual mapping
# 0 = not infrastructure
# 1 = infrastructure
infrastructure_mapping = {
    'Agriculture': [
        'Agriculture, Fishing and Forestry',
        'FY17 - Agriculture, Fishing and Forestry',
        1
    ],
    'Education': [
        'Education',
        'FY17 - Education',
        0
    ],
    'Energy & Extractives': [
        '(Historic)Electric Power & Other Energy',
        'Energy and Mineral Resources',
        'FY17 - Energy and Extractives',
        1
    ],
    'Financial Sector': [
        'Financial Sector',
        'FY17 - Financial Sector',
        0
    ],
    'Health': [
        '(Historic)Health and other social services',
        'FY17 - Health',
        'Health',
        0
    ],
    'Industry & Trade/Ser': [
        'Industry',
        'FY17 - Industry, Trade and Services',
        'Industry, Trade and Services',
        1
    ],
    'Info & Communication': [
        'FY17 - Information and Communications Technologies',
        'Digital Development',
        1
    ], # called "digital development" in api theme: https://www.devex.com/news/how-the-world-bank-s-work-on-digitalization-is-evolving-103075
    'Public Admin': [
        'FY17 - Public Administration',
        'Public Administration',
        0
    ],
    'Social Protection': [
        'FY17 - Social Protection',
        'Social Protection',
        'Social Sustainability and Inclusion',
        0
    ],
    'Transportation': [
        'FY17 - Transportation',
        'Transportation',
        1
    ],
    'Water/Sanit/Waste': [
        'FY17 - Water, Sanitation and Waste Management',
        'Water, Sanitation and Waste Management',
        1
    ]
}


# insert
with engine.connect() as conn:
    for condensed_name, values in infrastructure_mapping.items():
        infrastructure_flag = values[-1]
        
        conn.execute(text("""
            INSERT INTO wb_condensed_sector (wb_condensed_sector_name, infrastructure)
            VALUES (:name, :infra)
            ON DUPLICATE KEY UPDATE infrastructure = VALUES(infrastructure)
        """), {"name": condensed_name, "infra": bool(infrastructure_flag)})
    
    for condensed_name, values in infrastructure_mapping.items():
        major_sector_names = [v for v in values if isinstance(v, str)]
        
        for major_sector_name in major_sector_names:
            conn.execute(text("""
                UPDATE major_sector_lookup
                SET wb_condensed_sector_name = :condensed_name
                WHERE major_sector_name = :major_name
            """), {"condensed_name": condensed_name, "major_name": major_sector_name})
    
    conn.commit()