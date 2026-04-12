USE wb_proj_doc;
SELECT 
    COUNT(DISTINCT project_id) AS `Projects with Sector Data`,
    COUNT(DISTINCT CASE WHEN sector_percent != 0 THEN project_id END) AS sector_with_percent,
    COUNT(DISTINCT CASE WHEN sector_percent = 0 THEN project_id END) AS sector_without_percent
FROM project_sectors;

SELECT 
    p.project_id,
    msl.major_sector_code,
    msl.major_sector_name,
    sl.sector_code,
    sl.sector_name,
    ps.sector_percent
FROM projects p
JOIN project_major_sectors pms ON p.project_id = pms.project_id
JOIN major_sector_lookup msl ON pms.major_sector_code = msl.major_sector_code
JOIN project_sectors ps ON pms.project_major_sector_id = ps.project_major_sector_id
JOIN proj_sector_lookup sl ON ps.sector_code = sl.sector_code
ORDER BY p.project_id, msl.major_sector_code, sl.sector_code;



SELECT 
    (SELECT COUNT(*) FROM projects) AS total_projects,
    COUNT(DISTINCT project_id) AS projects_with_sector_data,
    COUNT(DISTINCT CASE WHEN sector_percent != 0 THEN project_id END) AS projects_with_nonzero_percent,
    COUNT(DISTINCT CASE WHEN sector_percent = 0 THEN project_id END) AS projects_with_zero_percent
FROM project_sectors;