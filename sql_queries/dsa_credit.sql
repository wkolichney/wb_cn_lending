USE wb_proj_doc;

CREATE TABLE IF NOT EXISTS credit_lookup(
	credit_id INT PRIMARY KEY,
    s_p VARCHAR(25),
    moody VARCHAR(25),
    fitch VARCHAR(25)
);



CREATE TABLE IF NOT EXISTS dsa_credit (
	dsa_credit_id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
	iso3 CHAR(3) NOT NULL,
    year INT NOT NULL,
    dsa VARCHAR(250),
    credit_id INT,
	FOREIGN KEY (iso3) REFERENCES country(iso3),
    FOREIGN KEY (credit_id) REFERENCES credit_lookup(credit_id)
);