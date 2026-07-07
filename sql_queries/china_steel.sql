USE wb_proj_doc;

CREATE TABLE IF NOT EXISTS china_steel(
year int4 PRIMARY KEY NOT NULL,
china_steel FLOAT NOT NULL,
world_steel FLOAT NOT NULL,
world_minus_china FLOAT NOT NULL,
china_share FLOAT NOT NULL
);

-- DROP TABLE IF EXISTS china_steel;

