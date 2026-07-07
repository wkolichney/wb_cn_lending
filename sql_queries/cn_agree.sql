USE wb_proj_doc;

CREATE TABLE un_cn_agree (
	id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
	iso3 CHAR(3) NOT NULL,
    year int4 NOT NULL,
    agree FLOAT NOT NULL,
    ideal_point_distance FLOAT NOT NULL,
    us_china CHAR(3) NOT NULL,
	FOREIGN KEY (iso3) REFERENCES country(iso3)
);

DROP TABLE IF EXISTS un_cn_agree;

SELECT * FROM un_cn_agree;