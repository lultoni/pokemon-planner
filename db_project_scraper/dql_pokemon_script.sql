-- 1. Abfragen über mehrere Tabellen mit Auswahlbedingungen
-- Beispiel A: Alle Pokémon finden, die vom Typ 'Feuer' sind.

SELECT p.Pokemon_Name, t.Typ_Name
FROM T_Pokemon p
JOIN T_Pokemon_Typen t ON p.Pokedex_Nr = t.Pokedex_Nr
WHERE t.Typ_Name = 'Feuer';

-- Beispiel B: Alle Pokémon anzeigen, die die Attacke 'Donnerblitz' erlernen können.

SELECT 
    p.Pokemon_Name, 
    lm.Art AS Erlernmethode,
    lm.Level
FROM T_Pokemon p
JOIN T_Pokemon_Attacken pa ON p.Pokedex_Nr = pa.Pokedex_Nr
JOIN T_Lernmethoden lm ON pa.Lernmethode_ID = lm.Lernmethode_ID -- NEUER JOIN
WHERE pa.Attacke_Name = 'Donnerblitz';

-- ------------------------------------------------------------
-- 2. Abfragen mit Aggregatsfunktionen & Gruppenbildungen
-- Beispiel A: Wie viele Pokémon gibt es pro Typ?

SELECT Typ_Name, COUNT(*) AS Anzahl_Pokemon
FROM T_Pokemon_Typen
GROUP BY Typ_Name
ORDER BY Anzahl_Pokemon DESC;

-- Beispiel B: Die durchschnittliche Stärke (Angriff) aller Pokémon berechnen.

SELECT AVG(Angriff) AS Durchschnittlicher_Angriff
FROM T_Basis_Stats;

-- ------------------------------------------------------------
-- 3. Abfrage mit JOIN
-- Beispiel A: Vollständige "Pokedex"-Liste mit Basis-Werten.

SELECT p.Pokedex_Nr, p.Pokemon_Name, b.KP, b.Angriff, b.Verteidigung, b.Sp_Angriff, b.Sp_Verteidigung, b.Initiative
FROM T_Pokemon p
JOIN T_Basis_Stats b ON p.Pokedex_Nr = b.Pokedex_Nr
ORDER BY p.Pokedex_Nr ASC;

-- Beispiel B: Wer entwickelt sich zu wem? (Self-Join Logik)

SELECT 
    p1.Pokemon_Name AS Basis_Pokemon, 
    'entwickelt sich zu' AS Info,
    p2.Pokemon_Name AS Entwicklung,
    m.Methoden_Name
FROM T_Entwicklung e
JOIN T_Pokemon p1 ON e.Von_Pokemon_Nr = p1.Pokedex_Nr
JOIN T_Pokemon p2 ON e.Zu_Pokemon_Nr = p2.Pokedex_Nr
JOIN T_Evolutions_Methoden m ON e.Methode_ID = m.Methode_ID;

-- --------------------------------------------------------------------------
-- 4. Views
-- Beispiel A: View für "Starke Attacken"

DROP VIEW IF EXISTS V_Starke_Attacken;

CREATE VIEW V_Starke_Attacken AS
SELECT Attacke_Name, Typ_Name, Staerke, Genauigkeit
FROM T_Attacken
WHERE Staerke >= 100;

SELECT * FROM V_Starke_Attacken;

-- Beispiel B: View für "Tank Pokémon" (Hohe Verteidigung)

DROP VIEW IF EXISTS V_Tank_Pokemon;

CREATE VIEW V_Tank_Pokemon AS
SELECT p.Pokemon_Name, b.Verteidigung, b.Sp_Verteidigung, b.KP
FROM T_Pokemon p
JOIN T_Basis_Stats b ON p.Pokedex_Nr = b.Pokedex_Nr
WHERE b.Verteidigung >= 100 OR b.Sp_Verteidigung >= 100;

SELECT * FROM V_Tank_Pokemon;

-- Beispiel C: View für V_Pokemon_Gesamtwerte (Base Stat Total)

DROP VIEW IF EXISTS V_Pokemon_Gesamtwerte;

CREATE VIEW V_Pokemon_Gesamtwerte AS
SELECT 
    p.Pokedex_Nr, 
    p.Pokemon_Name,
    b.KP,
    b.Angriff,
    b.Verteidigung,
    b.Sp_Angriff,
    b.Sp_Verteidigung,
    b.Initiative,
    (b.KP + b.Angriff + b.Verteidigung + b.Sp_Angriff + b.Sp_Verteidigung + b.Initiative) AS Gesamtwert
FROM T_Pokemon p
JOIN T_Basis_Stats b ON p.Pokedex_Nr = b.Pokedex_Nr;

SELECT * FROM V_Pokemon_Gesamtwerte
ORDER BY Gesamtwert DESC
LIMIT 5;
