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
