use wb_proj_doc;

CREATE TABLE IF NOT EXISTS trade_china (
	trade_china_id INT PRIMARY KEY AUTO_INCREMENT NOT NULL,
    iso3 CHAR(3),
    year INT,
    exports FLOAT,
    `gdp$2015` FLOAT,
    `export%gdp` FLOAT,
    FOREIGN KEY (iso3) REFERENCES country(iso3)
);

DROP TABLE IF EXISTS trade_china;