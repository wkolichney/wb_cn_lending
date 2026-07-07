use wb_proj_doc;
SHOW TABLES;

-- control variables
SELECT DISTINCT(indicator_code) FROM wb_indicator_pull;
SELECT * FROM wb_indicator_pull;
SELECT * FROM wb_indicators;

SELECT 
	wp.*,
    wb.indicator_name
FROM wb_indicator_pull AS wp
JOIN wb_indicators AS wb ON wp.indicator_code = wb.indicator_code
;


SELECT * FROM un_cn_agree;
SELECT * FROM trade_china;
SELECT * FROM taiwan_recognition;
SELECT * FROM oil_gas;
SELECT * FROM fdi;
SELECT * FROM dac_oda;
SELECT * FROM country_alternate;
SELECT * FROM dsa_credit;