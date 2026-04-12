# World Bank Projects
## Author: William Olichney
## Date Started: April 2026
#### Purpose: Pull World Bank project and project document data in order to compare Chinese development finance with World Bank development finance.

#### Step 1: Clone Repo
```
git clone https://github.com/wkolichney/wb_cn_lending
```

#### Step 2: Install Requirements
```
pip install requirements.txt
```

#### Step 3: Run SQL file
```
cd sql_queries
mysql -u root -p wb_proj_doc < proj_doc.sql
```

#### Step 4: Project API and Document API
```
cd ..
cd sql_insert_scripts
python insert_project.py
python insert_document.py
```
