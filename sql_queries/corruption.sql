USE wb_proj_doc;

-- Political corruption: V-Dem Public sector corruption index (v2x_pubcorr),
-- Coppedge et al. (2017), V-Dem-CY-Core v16. Range 0-1, higher = more corrupt.
CREATE TABLE IF NOT EXISTS corruption(
	corruption_id INT PRIMARY KEY AUTO_INCREMENT,
	iso3 CHAR(3) NOT NULL,
	year INT NOT NULL,
	v2x_pubcorr DECIMAL(4,3),
	FOREIGN KEY (iso3) REFERENCES country(iso3)
);
