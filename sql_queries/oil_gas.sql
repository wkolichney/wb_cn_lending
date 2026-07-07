USE wb_proj_doc;

CREATE TABLE IF NOT EXISTS oil_gas (
	oil_gas_id INT PRIMARY KEY AUTO_INCREMENT,
    year INT NOT NULL,
    iso3 CHAR(3),
    oil_prod FLOAT,
    oil_value FLOAT,
    gas_prod FLOAT,
    gas_value FLOAT,
    FOREIGN KEY(iso3) REFERENCES country(iso3)
    );
    
