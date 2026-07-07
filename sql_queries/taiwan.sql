USE wb_proj_doc;

CREATE TABLE IF NOT EXISTS taiwan_recognition (
	taiwan_id INT PRIMARY KEY AUTO_INCREMENT,
	iso3 CHAR(3) NOT NULL,
    year INT NOT NULL,
    taiwanrecognition BOOLEAN NOT NULL,
    FOREIGN KEY(iso3) REFERENCES country(iso3)
);
