-- =========================================================
-- AIR-21 : Intégration SQL
-- Schéma + chargement CSV + vues indicateurs
-- =========================================================

-- 0) Base de données
-- NOTE : Ces lignes sont commentées pour compatibilité éventuelle.
-- Pour MySQL, tu peux les décommenter si nécessaire.

 CREATE DATABASE IF NOT EXISTS airlines_sql;
--   DEFAULT CHARACTER SET utf8mb4
--   COLLATE utf8mb4_unicode_ci;
 USE airlines_sql;

-- =========================================================
-- 1) DDL : tables + index (AIR-22)
-- =========================================================

-- Suppression dans l'ordre inverse des dépendances
DROP TABLE IF EXISTS airline_scores;
DROP TABLE IF EXISTS airline_clustering_features;
DROP TABLE IF EXISTS airline_features;
DROP TABLE IF EXISTS region_summary;

-- 1.1) Table des features par compagnie
CREATE TABLE airline_features (
    airline              VARCHAR(100) NOT NULL,
    fleet_size           INT          NOT NULL,
    n_models             INT,
    diversity            DOUBLE,
    new_gen_share        DOUBLE,
    indice_modernite_v0  DOUBLE,
    indice_public        DOUBLE,
    indice_penalise      DOUBLE,
    n_a220               INT,
    n_787                INT,
    n_a350               INT,
    n_a330neo            INT,
    n_neo                INT,
    n_max                INT,
    pct_a220             DOUBLE,
    pct_787              DOUBLE,
    pct_a350             DOUBLE,
    pct_a330neo          DOUBLE,
    pct_neo              DOUBLE,
    pct_max              DOUBLE,
    pct_newgen_narrow    DOUBLE,
    pct_newgen_wide      DOUBLE,
    PRIMARY KEY (airline)
);

CREATE INDEX idx_af_fleet      ON airline_features(fleet_size);
CREATE INDEX idx_af_modernite  ON airline_features(indice_modernite_v0);
CREATE INDEX idx_af_newgen     ON airline_features(new_gen_share);

-- 1.2) Scores agrégés (AIR-9)
CREATE TABLE airline_scores (
    airline          VARCHAR(100) NOT NULL,
    fleet_size       INT          NOT NULL,
    diversity        DOUBLE,
    modernity_index  DOUBLE,
    version_v1       VARCHAR(10),
    qa_notes         TEXT,
    PRIMARY KEY (airline),
    CONSTRAINT fk_scores_airline
        FOREIGN KEY (airline) REFERENCES airline_features(airline)
        ON DELETE CASCADE
);

CREATE INDEX idx_scores_modernity ON airline_scores(modernity_index);

-- 1.3) Features pour clustering + cluster (AIR-15)
CREATE TABLE airline_clustering_features (
    airline              VARCHAR(100) NOT NULL,
    fleet_size           INT          NOT NULL,
    n_models             INT,
    diversity            DOUBLE,
    modernity_index      DOUBLE,
    new_gen_share        DOUBLE,
    pct_a220             DOUBLE,
    pct_787              DOUBLE,
    pct_a350             DOUBLE,
    pct_a330neo          DOUBLE,
    pct_neo              DOUBLE,
    pct_max              DOUBLE,
    pct_newgen_narrow    DOUBLE,
    pct_newgen_wide      DOUBLE,
    cluster              INT NOT NULL,
    PRIMARY KEY (airline),
    CONSTRAINT fk_clusterfeat_airline
        FOREIGN KEY (airline) REFERENCES airline_features(airline)
        ON DELETE CASCADE
);

CREATE INDEX idx_cluster_modernity ON airline_clustering_features(modernity_index);
CREATE INDEX idx_cluster_id        ON airline_clustering_features(cluster);

-- 1.4) Résumé régional (AIR-14)
CREATE TABLE region_summary (
    region               VARCHAR(50) NOT NULL,
    n_airlines           INT         NOT NULL,
    mean_modernity_index DOUBLE,
    top_airlines         TEXT,
    PRIMARY KEY (region)
);

-- =========================================================
-- 2) LOAD DATA : chargement CSV (AIR-23, MySQL uniquement)
-- ATTENTION : exécuter ce script depuis le dossier racine du projet
-- (là où se trouve le dossier "release").
-- =========================================================

-- 2.1) airline_features
LOAD DATA LOCAL INFILE 'release/features_by_airline.csv'
INTO TABLE airline_features
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(airline,
 fleet_size,
 n_models,
 diversity,
 new_gen_share,
 indice_modernite_v0,
 indice_public,
 indice_penalise,
 n_a220,
 n_787,
 n_a350,
 n_a330neo,
 n_neo,
 n_max,
 pct_a220,
 pct_787,
 pct_a350,
 pct_a330neo,
 pct_neo,
 pct_max,
 pct_newgen_narrow,
 pct_newgen_wide
);

-- 2.2) airline_scores
LOAD DATA LOCAL INFILE 'release/airline_scores.csv'
INTO TABLE airline_scores
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(airline,
 fleet_size,
 diversity,
 modernity_index,
 version_v1,
 qa_notes
);

-- 2.3) airline_clustering_features (AIR-15 + clusters)
LOAD DATA LOCAL INFILE 'release/air15_clusters_by_airline.csv'
INTO TABLE airline_clustering_features
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(airline,
 fleet_size,
 n_models,
 diversity,
 modernity_index,
 new_gen_share,
 pct_a220,
 pct_787,
 pct_a350,
 pct_a330neo,
 pct_neo,
 pct_max,
 pct_newgen_narrow,
 pct_newgen_wide,
 cluster
);

-- 2.4) region_summary
LOAD DATA LOCAL INFILE 'release/region_summary.csv'
INTO TABLE region_summary
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
       ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(region,
 n_airlines,
 mean_modernity_index,
 top_airlines
);

-- =========================================================
-- 3) Vues indicateurs
-- =========================================================

-- 3.1) Vue complète
CREATE OR REPLACE VIEW v_airline_full AS
SELECT
    f.airline,
    f.fleet_size,
    f.n_models,
    f.diversity              AS diversity_features,
    f.new_gen_share          AS new_gen_share_features,
    f.indice_modernite_v0,
    f.indice_public,
    f.indice_penalise,
    s.modernity_index        AS modernity_index_score,
    s.qa_notes,
    c.modernity_index        AS modernity_index_cluster,
    c.new_gen_share          AS new_gen_share_cluster,
    f.pct_a220,
    f.pct_787,
    f.pct_a350,
    f.pct_a330neo,
    f.pct_neo,
    f.pct_max,
    f.pct_newgen_narrow,
    f.pct_newgen_wide,
    c.cluster
FROM airline_features f
LEFT JOIN airline_scores s
       ON s.airline = f.airline
LEFT JOIN airline_clustering_features c
       ON c.airline = f.airline;

-- 3.2) Top compagnies par modernité
CREATE OR REPLACE VIEW v_top_airlines_modernity AS
SELECT
    s.airline,
    s.modernity_index,
    f.fleet_size,
    f.diversity,
    f.new_gen_share
FROM airline_scores s
JOIN airline_features f
  ON f.airline = s.airline
ORDER BY s.modernity_index DESC, f.fleet_size DESC
LIMIT 50;

-- 3.3) Index moyen par région
CREATE OR REPLACE VIEW v_region_modernity AS
SELECT
    region,
    n_airlines,
    mean_modernity_index,
    top_airlines
FROM region_summary;


-- =========================================================
-- FIN AIR-21
-- =========================================================
