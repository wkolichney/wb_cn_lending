USE wb_proj_doc;

-- UCDP/PRIO Armed Conflict Dataset (ACD) v26.1 -- lean country-year subset.
-- Source: UcdpPrioConflict_v26_1.csv
-- Grain: one row per conflict x year x location-country. The source lists
-- interstate conflicts with a comma-separated `location`; the loader explodes
-- that into one row per country and attaches iso3 (name match against
-- country_alternate), so conflict_id is NOT unique here -- a surrogate PK is used.
-- The source codes missing data as -99 (and blanks); the loader maps both to NULL.
-- Only the columns needed to build a per-country-year conflict indicator are kept;
-- actor names/IDs, territory, gwno codes, the start/end date + precision fields,
-- and version are dropped (link is by location name, not gwno).
CREATE TABLE IF NOT EXISTS ucdp_conflict (
    conflict_year_id     INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    conflict_id          INT NOT NULL,
    location             VARCHAR(255),     -- single country name (exploded from the source's comma list)
    iso3                 CHAR(3) NOT NULL, -- resolved from location via country_alternate at load
    year                 INT NOT NULL,
    incompatibility      INT,              -- 1=territory, 2=government, 3=both
    intensity_level      INT,              -- 1=minor (25-999), 2=war (>=1000)
    cumulative_intensity INT,              -- 0/1 dummy: has conflict ever exceeded 1000 deaths
    type_of_conflict     INT,              -- 1=extrasystemic,2=interstate,3=intrastate,4=internationalized
    FOREIGN KEY (iso3) REFERENCES country(iso3),
    KEY idx_conflict_year (conflict_id, year),
    KEY idx_iso3_year (iso3, year)
);

SELECT * FROM ucdp_conflict LIMIT 20;
-- DROP TABLE IF EXISTS ucdp_conflict;
