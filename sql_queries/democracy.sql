USE wb_proj_doc;

CREATE TABLE IF NOT EXISTS democracy (
 polity_id INT PRIMARY KEY AUTO_INCREMENT,
 iso3 CHAR(3) NOT NULL,
 year INT NOT NULL,
 polity2 INT,
 FOREIGN KEY (iso3) REFERENCES country(iso3)
);

