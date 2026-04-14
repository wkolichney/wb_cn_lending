USE wb_proj_doc;
SHOW TABLES;
SHOW COLUMNS FROM documents;
SHOW COLUMNS FROM projects;
SHOW COLUMNS FROM project_sectors;
SHOW COLUMNS FROM project_major_sectors;
SHOW COLUMNS FROM major_sector_lookup;
SHOW COLUMNS FROM proj_sector_lookup;

-- project with document dates
SELECT
p.project_id,
p.countryshortname,
p.boardapprovaldate,
d.docdt, # is this the date I need from docs?
d.document_type,
d.document_id
FROM projects as p
JOIN documents as d ON p.project_id = d.project_id;
-- Sector look --

SELECT 
p.project_id,
msl.major_sector_name
FROM projects as p
JOIN project_major_sectors as pms on pms.project_id = p.project_id
JOIN major_sector_lookup AS msl ON msl.major_sector_code = pms.major_sector_code;


SELECT 
p.project_id,
psl.sector_name,
ps.sector_percent
FROM projects as p
JOIN project_sectors AS ps ON ps.project_id = p.project_id 
JOIN proj_sector_lookup AS psl ON psl.sector_code = ps.sector_code;


