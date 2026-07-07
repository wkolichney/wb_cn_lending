use wb_proj_doc;



CREATE TABLE IF NOT EXISTS bilateral_fdi (
	fdi_id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    year INT,
    flow FLOAT,
    iso3 CHAR(3),
	FOREIGN KEY (iso3) REFERENCES country(iso3)
);

SELECT * FROM bilateral_fdi;