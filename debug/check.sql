USE wb_proj_doc;

ALTER TABLE doc_theme DROP FOREIGN KEY doc_theme_ibfk_2;
ALTER TABLE doc_theme_lookup MODIFY theme_name VARCHAR(500);
ALTER TABLE doc_theme MODIFY theme_name VARCHAR(500);
ALTER TABLE doc_theme ADD FOREIGN KEY (theme_name) REFERENCES doc_theme_lookup(theme_name);