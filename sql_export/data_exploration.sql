USE wb_proj_doc;
SHOW TABLES;
SELECT * FROM doc_theme_lookup;
SELECT * 
FROM doc_theme
WHERE theme_name = 'etc.)';

SELECT 
	d.document_name,
    dt.theme_name
FROM documents as d
JOIN doc_theme as dt ON dt.document_id = d.document_id
WHERE d.document_id = 40078489;