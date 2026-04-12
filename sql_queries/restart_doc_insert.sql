USE wb_proj_doc;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE doc_sector;
TRUNCATE TABLE doc_theme;
TRUNCATE TABLE doc_sub_sector;
TRUNCATE TABLE doc_country;
TRUNCATE TABLE doc_sector_lookup;
TRUNCATE TABLE doc_theme_lookup;
TRUNCATE TABLE doc_sub_sector_lookup;
TRUNCATE TABLE documents;
SET FOREIGN_KEY_CHECKS = 1;

SELECT * FROM documents;