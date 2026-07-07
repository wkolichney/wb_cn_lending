-- ============================================================================
-- data_availability.sql
-- Quick coverage checks for every dataset in wb_proj_doc.
-- Run:  mysql -u root -p wb_proj_doc < data_availability.sql
-- ============================================================================
USE wb_proj_doc;

-- --- 1. World Bank project / document core ---------------------------------
SELECT 'projects'  AS dataset, COUNT(*) AS rows_,
       COUNT(DISTINCT countryshortname) AS countries,
       MIN(YEAR(boardapprovaldate)) AS year_min,
       MAX(YEAR(boardapprovaldate)) AS year_max
FROM projects
UNION ALL
SELECT 'documents', COUNT(*), COUNT(DISTINCT project_id),
       MIN(YEAR(docdt)), MAX(YEAR(docdt))
FROM documents;

-- documents by type (which document types are available, and how many)
SELECT document_type, COUNT(*) AS n
FROM documents
GROUP BY document_type
ORDER BY n DESC;

-- --- 2. Country coverage ----------------------------------------------------
SELECT COUNT(*)                                   AS country_rows,
       SUM(iso3 IS NOT NULL)                      AS with_iso3,
       (SELECT COUNT(*) FROM country_alternate)   AS crosswalk_spellings
FROM country;

-- --- 3. Country-year control variables --------------------------------------
-- One row per dataset: total rows, distinct countries (iso3), and year span.
-- `pct_countries` is coverage relative to the 189 countries that carry an iso3.
SELECT dataset, rows_, countries,
       ROUND(100 * countries / (SELECT COUNT(*) FROM country WHERE iso3 IS NOT NULL)) AS pct_countries,
       year_min, year_max
FROM (
    SELECT 'wb_indicator_pull'  AS dataset, COUNT(*) rows_, COUNT(DISTINCT iso3) countries, MIN(year) year_min, MAX(year) year_max FROM wb_indicator_pull
    UNION ALL SELECT 'un_cn_agree',        COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM un_cn_agree
    UNION ALL SELECT 'trade_china',        COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM trade_china
    UNION ALL SELECT 'taiwan_recognition', COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM taiwan_recognition
    UNION ALL SELECT 'dsa_credit',         COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM dsa_credit
    UNION ALL SELECT 'oil_gas',            COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM oil_gas
    UNION ALL SELECT 'democracy',          COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM democracy
    UNION ALL SELECT 'corruption',         COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM corruption
    UNION ALL SELECT 'dac_oda',            COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM dac_oda
    UNION ALL SELECT 'bilateral_fdi',      COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM bilateral_fdi
    UNION ALL SELECT 'ucdp_conflict',      COUNT(*), COUNT(DISTINCT iso3), MIN(year), MAX(year) FROM ucdp_conflict
) t
ORDER BY pct_countries DESC, dataset;

-- --- 4. Global (non-country) series -----------------------------------------
SELECT 'china_steel' AS dataset, COUNT(*) AS rows_, MIN(year) AS year_min, MAX(year) AS year_max
FROM china_steel;

-- --- 5. Reference / lookup tables (row counts) ------------------------------
SELECT 'wb_indicators' AS lookup_table, COUNT(*) AS rows_ FROM wb_indicators
UNION ALL SELECT 'credit_lookup',        COUNT(*) FROM credit_lookup
UNION ALL SELECT 'major_sector_lookup',  COUNT(*) FROM major_sector_lookup
UNION ALL SELECT 'wb_condensed_sector',  COUNT(*) FROM wb_condensed_sector
UNION ALL SELECT 'proj_sector_lookup',   COUNT(*) FROM proj_sector_lookup
UNION ALL SELECT 'doc_theme_lookup',     COUNT(*) FROM doc_theme_lookup
UNION ALL SELECT 'doc_sector_lookup',    COUNT(*) FROM doc_sector_lookup
UNION ALL SELECT 'doc_sub_sector_lookup',COUNT(*) FROM doc_sub_sector_lookup;
