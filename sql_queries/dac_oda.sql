USE wb_proj_doc;
SELECT * FROM country;

CREATE TABLE IF NOT EXISTS dac_oda (
	dac_oda_id INT PRIMARY KEY AUTO_INCREMENT,
    donor varchar(250),
    iso3 CHAR(3), -- recipient
    year INT,
    value float,
    FOREIGN KEY (iso3) REFERENCES country(iso3)
);

SELECT * FROM dac_oda;
DROP TABLE IF EXISTS dac_oda;
    
    