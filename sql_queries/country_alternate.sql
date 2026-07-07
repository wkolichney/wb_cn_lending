use wb_proj_doc;

CREATE TABLE IF NOT EXISTS country_alternate (
	alternate_id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    iso3 CHAR(3),                                       -- NULL allowed: in-scope regions with no iso3
    iso2 CHAR(2),
    countryshortname VARCHAR(500),
    UNIQUE KEY uq_alt_name (countryshortname),
    FOREIGN KEY (iso3) REFERENCES country(iso3)
);

SELECT * FROM country_alternate;