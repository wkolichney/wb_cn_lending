USE wb_proj_doc;

CREATE TABLE IF NOT EXISTS wb_indicators (
	indicator_code VARCHAR(250) PRIMARY KEY NOT NULL,
	indicator_name TEXT NOT NULL
    );
    
CREATE TABLE IF NOT EXISTS wb_indicator_pull (
	indicator_index INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    iso3 CHAR(3),
    value float,
    indicator_code VARCHAR(250) NOT NULL,
    year INT,
    FOREIGN KEY (indicator_code) REFERENCES wb_indicators(indicator_code),
    FOREIGN KEY (iso3) REFERENCES country(iso3)
    );
    
SELECT DISTINCT countryshortname FROM country;
-- yep, didn't catch korea, venezuela, Lao because of different naming. I think ISO is needed

-- At most, 291 projects will be filtered out of wb indicator stuff
SELECT COUNT(p.project_id)  
FROM projects AS p
JOIN country AS c ON c.countryshortname = p.countryshortname
WHERE c.iso3 IS NULL
AND p.boardapprovaldate >= '2000-01-01'
;

SELECT * FROM wb_indicators;
SELECT * FROM wb_indicator_pull;

-- DROP TABLE IF EXISTS wb_indicators;
-- DROP TABLE IF EXISTS wb_indicator_pull;


