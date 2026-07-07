USE wb_proj_doc;
SHOW TABLES;

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

ALTER TABLE doc_theme_lookup MODIFY theme_name VARCHAR(500);
ALTER TABLE doc_theme MODIFY theme_name VARCHAR(500);

ALTER TABLE doc_sub_sector_lookup MODIFY sub_sector_name TEXT;
ALTER TABLE doc_sub_sector MODIFY sub_sector_name TEXT;


ALTER TABLE documents MODIFY pdfurl TEXT;
ALTER TABLE documents MODIFY txturl TEXT;
ALTER TABLE documents MODIFY url TEXT;
ALTER TABLE documents MODIFY display_title TEXT;
ALTER TABLE documents MODIFY document_name TEXT;

-- WB projects refer to 'Somalia' and "Somalia, Federal Republic of", but we've been using country names as a unique key
-- and as a foreign key in multiple tables. This code below fixes that duplication and corrects across keys
-- cant simply do ISO as primary key because WB proj 'countries' don't always have iso-able names
BEGIN;

UPDATE projects SET countryshortname = 'Somalia' 
WHERE countryshortname = 'Somalia, Federal Republic of';

UPDATE doc_country SET countryshortname = 'Somalia' 
WHERE countryshortname = 'Somalia, Federal Republic of';

DELETE FROM country 
WHERE countryshortname = 'Somalia, Federal Republic of';

-- Verify before committing
SELECT * FROM country WHERE countryshortname LIKE 'Somalia%';

COMMIT;

-- add iso3 to country table
ALTER TABLE country
ADD COLUMN iso3 CHAR(3) NULL UNIQUE;

-- add iso2, useful for IMF queries
ALTER TABLE country
ADD COLUMN iso2 CHAR(2) UNIQUE;

-- FK between projects and country
ALTER TABLE projects
ADD CONSTRAINT fk_projects_country
FOREIGN KEY (countryshortname)
REFERENCES country(countryshortname);