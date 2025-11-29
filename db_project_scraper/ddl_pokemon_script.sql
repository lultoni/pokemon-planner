USE data_test;

-- -----------------------------------------------------
-- SCHRITT 0: ALTE TABELLEN LÖSCHEN (CLEANUP)
-- Wir deaktivieren kurz die Prüfung der Fremdschlüssel,
-- um Lösch-Fehler zu vermeiden.
-- -----------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS T_Pokemon_Attacken;
DROP TABLE IF EXISTS T_Entwicklung;
DROP TABLE IF EXISTS T_Evolutions_Methoden;
DROP TABLE IF EXISTS T_Pokemon_Typen;
DROP TABLE IF EXISTS T_Basis_Stats;
DROP TABLE IF EXISTS T_Pokemon;
DROP TABLE IF EXISTS T_Attacken;
DROP TABLE IF EXISTS T_Lernmethoden;
DROP TABLE IF EXISTS T_Typen;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------
-- SCHRITT 1: NEUE STRUKTUR ANLEGEN
-- -----------------------------------------------------

-- 1. T_Typen
CREATE TABLE T_Typen (
    Typ_Name VARCHAR(50) NOT NULL PRIMARY KEY
);

-- 2. T_Lernmethoden (NEU)
CREATE TABLE T_Lernmethoden (
    Erlernmethode VARCHAR(50) NOT NULL PRIMARY KEY
);

-- 3. T_Attacken
CREATE TABLE T_Attacken (
    Attacke_Name VARCHAR(100) NOT NULL PRIMARY KEY,
    Staerke INT UNSIGNED DEFAULT NULL,
    Genauigkeit INT UNSIGNED DEFAULT NULL CHECK (Genauigkeit BETWEEN 0 AND 100),
    AP INT UNSIGNED NOT NULL DEFAULT 0,
    Typ_Name VARCHAR(50) NOT NULL,
    
    CONSTRAINT fk_attacken_typ FOREIGN KEY (Typ_Name)
        REFERENCES T_Typen (Typ_Name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
CREATE INDEX idx_attacken_typ ON T_Attacken (Typ_Name);

-- 4. T_Pokemon
CREATE TABLE T_Pokemon (
    Pokedex_Nr INT UNSIGNED NOT NULL PRIMARY KEY CHECK (Pokedex_Nr BETWEEN 1 AND 999),
    Pokemon_Name VARCHAR(100) NOT NULL,
    UNIQUE KEY uk_pokemon_name (Pokemon_Name)
);

-- 5. T_Basis_Stats
CREATE TABLE T_Basis_Stats (
    Pokedex_Nr INT UNSIGNED NOT NULL PRIMARY KEY,
    KP INT UNSIGNED NOT NULL,
    Angriff INT UNSIGNED NOT NULL,
    Verteidigung INT UNSIGNED NOT NULL,
    Sp_Angriff INT UNSIGNED NOT NULL,
    Sp_Verteidigung INT UNSIGNED NOT NULL,
    Initiative INT UNSIGNED NOT NULL,
    
    CONSTRAINT fk_basis_pokemon FOREIGN KEY (Pokedex_Nr)
        REFERENCES T_Pokemon (Pokedex_Nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 6. T_Pokemon_Typen
CREATE TABLE T_Pokemon_Typen (
    Pokedex_Nr INT UNSIGNED NOT NULL,
    Typ_Name VARCHAR(50) NOT NULL,
    PRIMARY KEY (Pokedex_Nr, Typ_Name),
    
    CONSTRAINT fk_poktyp_pokemon FOREIGN KEY (Pokedex_Nr)
        REFERENCES T_Pokemon (Pokedex_Nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_poktyp_typ FOREIGN KEY (Typ_Name)
        REFERENCES T_Typen (Typ_Name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
CREATE INDEX idx_poktypen_typ ON T_Pokemon_Typen (Typ_Name);

-- 7. T_Evolutions_Methoden
CREATE TABLE T_Evolutions_Methoden (
    Methode_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Methoden_Name VARCHAR(150) NOT NULL,
    Stein_Name VARCHAR(100) DEFAULT NULL,
    UNIQUE KEY uk_evo_method_stein (Methoden_Name, Stein_Name)
);

DROP TABLE IF EXISTS T_Entwicklung;

CREATE TABLE T_Entwicklung (
    Evolutions_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Von_Pokemon_Nr INT UNSIGNED NOT NULL,
    Zu_Pokemon_Nr INT UNSIGNED NOT NULL,
    Methode_ID INT NOT NULL,
    Level INT UNSIGNED DEFAULT NULL CHECK (Level BETWEEN 1 AND 100),

    CONSTRAINT fk_entw_von FOREIGN KEY (Von_Pokemon_Nr)
        REFERENCES T_Pokemon (Pokedex_Nr)
        -- WICHTIG: Hier muss RESTRICT stehen, sonst Fehler 3823
        ON UPDATE RESTRICT 
        ON DELETE RESTRICT,
        
    CONSTRAINT fk_entw_zu FOREIGN KEY (Zu_Pokemon_Nr)
        REFERENCES T_Pokemon (Pokedex_Nr)
        -- WICHTIG: Hier muss RESTRICT stehen, sonst Fehler 3823
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
        
    CONSTRAINT fk_entw_method FOREIGN KEY (Methode_ID)
        REFERENCES T_Evolutions_Methoden (Methode_ID)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE INDEX idx_entw_von ON T_Entwicklung (Von_Pokemon_Nr);
CREATE INDEX idx_entw_zu ON T_Entwicklung (Zu_Pokemon_Nr);

-- 9. T_Pokemon_Attacken
CREATE TABLE T_Pokemon_Attacken (
    Pokemon_Attacken_ID INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    Pokedex_Nr INT UNSIGNED NOT NULL,
    Attacke_Name VARCHAR(100) NOT NULL,
    Erlernmethode VARCHAR(50) NOT NULL,
    Level INT UNSIGNED DEFAULT NULL CHECK (Level BETWEEN 1 AND 100),
    Voraussetzung VARCHAR(100) DEFAULT NULL,
    
    UNIQUE KEY uk_pokemon_attacke (Pokedex_Nr, Attacke_Name, Erlernmethode),

    CONSTRAINT fk_pokatk_pokemon FOREIGN KEY (Pokedex_Nr)
        REFERENCES T_Pokemon (Pokedex_Nr)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_pokatk_attacke FOREIGN KEY (Attacke_Name)
        REFERENCES T_Attacken (Attacke_Name)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_pokatk_methode FOREIGN KEY (Erlernmethode)
        REFERENCES T_Lernmethoden (Erlernmethode)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
CREATE INDEX idx_pokatk_attacke ON T_Pokemon_Attacken (Attacke_Name);
CREATE INDEX idx_pokatk_erlernmethode ON T_Pokemon_Attacken (Erlernmethode);