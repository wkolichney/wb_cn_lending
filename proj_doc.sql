CREATE DATABASE IF NOT EXISTS wb_proj_doc;
USE wb_proj_doc;

-- MAIN PROJECT TABLE --
CREATE TABLE IF NOT EXISTS projects (
    project_id VARCHAR(255) PRIMARY KEY NOT NULL,
    project_name VARCHAR(255),
    countryshortname VARCHAR(255),
    curr_ibrd_commitment DECIMAL(20, 2),
    idacommamt DECIMAL(20, 2),
    totalamt DECIMAL(20, 2),
    grantamt DECIMAL(20, 2),
    lendprojectcost DECIMAL(20, 2),
    boardapprovaldate DATE,
    closingdate DATE,
    envassesmentcategorycode CHAR(1)
);

-- CHILD TABLE PROJECT - MAJOR SECTOR --
CREATE TABLE IF NOT EXISTS project_major_sectors (
    project_major_sector_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id VARCHAR(255) NOT NULL,     -- FK points UP to projects
    major_sector_code CHAR(3) NOT NULL,   -- FK points to lookup
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (major_sector_code) REFERENCES major_sector_lookup(major_sector_code)
);

-- LOOKUP TABLE FOR MAJOR SECTORS --
CREATE TABLE IF NOT EXISTS major_sector_lookup (
    major_sector_code CHAR(3) PRIMARY KEY NOT NULL,
    major_sector_name VARCHAR(255)
);

-- CHILD TABLE PROJECT - SECTOR --
CREATE TABLE IF NOT EXISTS project_sectors (
    project_sector_id INT PRIMARY KEY AUTO_INCREMENT,
    project_id VARCHAR(255) NOT NULL,     -- shortcut FK
    sector_code CHAR(3) NOT NULL,         -- FK points to lookup
    sector_percent DECIMAL(5, 2),         -- never seen anything other than yet
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (project_major_sector_id) REFERENCES project_major_sectors(id),
    FOREIGN KEY (sector_code) REFERENCES sector_lookup(sector_code)
);

-- LOOKUP TABLE SECTOR --
CREATE TABLE IF NOT EXISTS proj_sector_lookup (
    sector_code CHAR(3) PRIMARY KEY NOT NULL,
    sector_name VARCHAR(255),
);


-- Lookup table for country and region information
CREATE TABLE IF NOT EXISTS country (
    countryshortname VARCHAR(255) PRIMARY KEY NOT NULL,
    regionname VARCHAR(255)
);


-- one to many relationship for implementing agencies and borrowers --
CREATE TABLE IF NOT EXISTS impagency (
    impagency_id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    impagency_name VARCHAR(255),
    project_id INT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

CREATE TABLE IF NOT EXISTS borrower (
    borrower_id INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
    borrower_name VARCHAR(255),
    project_id INT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);

-- one to many relationship (a project can have many documents)
CREATE TABLE IF NOT EXISTS documents (
    document_id INT PRIMARY KEY NOT NULL,
    document_name VARCHAR(255), -- called 'docna' in API
    document_type VARCHAR(255), -- "called docty"
    prdln VARCHAR(255), -- Something about "Product line (lending)" - unsure what means
    lndinstr VARCHAR(255), -- lending instrument. API allows for one-to-many, but never seen more than one

    -- DATES --
    docdt DATE, -- document date
    datestored DATE, -- date stored in database (assuming, no documentation)
    disclosure_date DATE, -- "disclosure date", but not sure what this means
    last_modified_date DATE,

    -- URLS --
    pdfurl VARCHAR(255), -- URL to PDF version of document
    txturl VARCHAR(255), -- URL to text version of document
    url VARCHAR(255), -- URL to document page on WB website

    -- MISC --
    maj_document_type VARCHAR(255), -- "majdocty" in API; major document type, more umbrella category than document_type
    disclstat VARCHAR(255), -- disclosure status
    versiontype VARCHAR(255), -- unsure meaning
    --prdln_exact VARCHAR(255) -- I dont think i need because ive never seen a difference with this and prdln, but could be wrong

    -- CITATION LIKE --
    author VARCHAR(255), -- in API, they give room for this to be a one-to-many relationship, but never seen more than one author
    security_class VARCHAR(255), -- "seccl" in API. WB misspelled "security" as "seurity" in documentation - lol
    lang VARCHAR(255),
    repnb VARCHAR(255), -- report number
    volnb INT, -- volume number
    display_title VARCHAR(255), -- title + volume name
    chronical_docm_id VARCHAR(255), -- Alternate document ID
    guid VARCHAR(255), -- Alternate document ID
    owner VARCHAR(255), -- Owning unit in the Bank

    --available_in VARCHAR(255) - seems useless cuz of lang
    -- FOREIGN KEYS --
    project_id INT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
);

-- DOCUMENT COUNTRY CHILD TABLE --
CREATE TABLE IF NOT EXISTS doc_country (
    doc_country_id INT PRIMARY KEY NOT NULL AUTO_INCREMENT, -- surrogate key for the many-to-many relationship
    countryshortname VARCHAR(255),
    document_id INT,
    FOREIGN KEY (document_id) REFERENCES documents(document_id),
    FOREIGN KEY (countryshortname) REFERENCES country(countryshortname)
);


-- A document can have multiple themes, a many-to-many relationship, so we need a join table. The theme name is stored here for simplicity, but could be normalized into a separate lookup table if desired.
CREATE TABLE IF NOT EXISTS doc_theme ( -- BEWARE, sometimes there's 'theme' and 'majtheme'. NO CLUE WHY
    doc_theme_id INT PRIMARY KEY NOT NULL, -- surrogate key for the many-to-many relationship
    theme_name VARCHAR(255),
    document_id INT,
    FOREIGN KEY (document_id) REFERENCES documents(document_id),
    FOREIGN KEY (theme_name) REFERENCES doc_theme_lookup(theme_name)
);

-- lookup table for themes, which are used in the doc_theme table
CREATE TABLE IF NOT EXISTS doc_theme_lookup (
    theme_name VARCHAR(255) PRIMARY KEY NOT NULL
);

-- A document can have sectors, a many-to-many relationship, so we need a join table. The theme name is stored here for simplicity, but could be normalized into a separate lookup table if desired.
CREATE TABLE IF NOT EXISTS doc_sector (
    doc_sector_id INT PRIMARY KEY NOT NULL, -- surrogate key for the many-to-many relationship
    sector_name VARCHAR(255),
    document_id INT,
    FOREIGN KEY (document_id) REFERENCES documents(document_id),
    FOREIGN KEY (sector_name) REFERENCES doc_sector_lookup(sector_name)
);

-- lookup table for sectors, which are used in the doc_sector table
CREATE TABLE IF NOT EXISTS doc_sector_lookup (
    sector_name VARCHAR(255) PRIMARY KEY NOT NULL
);

-- A document can have subsectors, a many-to-many relationship, so we need a join table. The theme name is stored here for simplicity, but could be normalized into a separate lookup table if desired.
CREATE TABLE IF NOT EXISTS doc_sub_sector (
    doc_sub_sector_id INT PRIMARY KEY NOT NULL, -- surrogate key for the many-to-many relationship
    sub_sector_name VARCHAR(255),
    document_id INT,
    FOREIGN KEY (document_id) REFERENCES documents(document_id),
    FOREIGN KEY (sub_sector_name) REFERENCES doc_sub_sector_lookup(sub_sector_name)
);

-- lookup table for sectors, which are used in the doc_sector table
CREATE TABLE IF NOT EXISTS doc_sub_sector_lookup (
    sub_sector_name VARCHAR(255) PRIMARY KEY NOT NULL
);

