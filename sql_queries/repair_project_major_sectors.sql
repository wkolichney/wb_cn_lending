-- Repair duplicate project_major_sectors rows (one-off, Oct 2026).
--
-- The WB API sometimes lists a major sector twice for one project (legacy name +
-- "FY17 - " name). insert_project.py made one project_major_sectors row per entry and
-- then joined sub-sectors on (project_id, major_sector_code), so every sub-sector of
-- those 389 (project, major sector) pairs was attached to BOTH parent rows and its
-- percentage counted twice. Each pair's two parents carry identical sub-sector sets,
-- so keep the lower id and drop the other parent together with its sub-sector rows.
--
-- Backup taken first: wb_cn_lending_db_backup_20261023/project_sectors_tables_before_repair.sql

USE wb_proj_doc;

START TRANSACTION;

CREATE TEMPORARY TABLE pms_extra AS
SELECT pms.project_major_sector_id
FROM project_major_sectors pms
JOIN (
    SELECT project_id, major_sector_code, MIN(project_major_sector_id) AS keep_id
    FROM project_major_sectors
    GROUP BY project_id, major_sector_code
    HAVING COUNT(*) > 1
) d ON d.project_id = pms.project_id
   AND d.major_sector_code = pms.major_sector_code
   AND pms.project_major_sector_id <> d.keep_id;

-- child rows first (FK project_sectors -> project_major_sectors)
DELETE ps FROM project_sectors ps
JOIN pms_extra x ON x.project_major_sector_id = ps.project_major_sector_id;

DELETE pms FROM project_major_sectors pms
JOIN pms_extra x ON x.project_major_sector_id = pms.project_major_sector_id;

COMMIT;

DROP TEMPORARY TABLE pms_extra;

-- guard against it happening again
ALTER TABLE project_major_sectors
    ADD CONSTRAINT uq_pms_project_major UNIQUE (project_id, major_sector_code);
ALTER TABLE project_sectors
    ADD CONSTRAINT uq_ps_parent_sector UNIQUE (project_major_sector_id, sector_code);
