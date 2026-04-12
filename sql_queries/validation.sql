USE wb_proj_doc;

UPDATE country
SET regionname = countryshortname
WHERE regionname IS NULL;

SELECT * FROM country
WHERE regionname IS NULL; -- This should return 0 rows if sucessful


UPDATE country
SET regionname = countryshortname
WHERE regionname = 'Other';

SELECT * FROM country
WHERE regionname = 'Other'; -- should only show up if countryshortname is also 'Other'

ALTER TABLE doc_theme_lookup MODIFY theme_name TEXT;
ALTER TABLE doc_theme MODIFY theme_name TEXT;
ALTER TABLE doc_sub_sector_lookup MODIFY sub_sector_name TEXT;
ALTER TABLE doc_sub_sector MODIFY sub_sector_name TEXT;


ALTER TABLE documents MODIFY pdfurl TEXT;
ALTER TABLE documents MODIFY txturl TEXT;
ALTER TABLE documents MODIFY url TEXT;
ALTER TABLE documents MODIFY display_title TEXT;
ALTER TABLE documents MODIFY document_name TEXT;
