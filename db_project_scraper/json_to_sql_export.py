#!/usr/bin/env python3
"""
json_to_sql_export.py

Liest information_storage/pokemon_knowledge_cache.json ein
und erstellt INSERT-Statements für die SQL-Tabellen:
T_Typen, T_Attacken, T_Pokemon, T_Basis_Stats, T_Pokemon_Typen,
T_Evolutions_Methoden, T_Entwicklung, T_Pokemon_Attacken

Speichert die SQL-Befehle in pokemon_export.sql.
"""

import json
import os
import re
from collections import OrderedDict

# ---------- Hilfsfunktionen ----------
def sql_str(s):
    """Escape und '...' für SQL; None -> NULL"""
    if s is None:
        return "NULL"
    s = str(s)
    s = s.replace("'", "''")
    return f"'{s}'"

def sql_int_or_null(v):
    if v is None:
        return "NULL"
    try:
        return str(int(v))
    except Exception:
        return "NULL"

def extract_number_from_id(id_str):
    """Zieht führende Ziffern aus IDs wie '003' oder '003g1' -> 3"""
    if id_str is None:
        return None
    m = re.match(r'0*([0-9]+)', str(id_str))
    if m:
        return int(m.group(1))
    # fallback: search any digits
    m2 = re.search(r'([0-9]+)', str(id_str))
    if m2:
        return int(m2.group(1))
    return None

# ---------- Pfade ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_JSON = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "pokemon_knowledge_cache.json"))
OUTPUT_SQL = os.path.abspath(os.path.join(BASE_DIR, "pokemon_export.sql"))

# Falls du von ausserhalb starten willst, kannst du hier den Pfad ändern:
json_path = DEFAULT_JSON

if not os.path.exists(json_path):
    raise FileNotFoundError(f"JSON file not found: {json_path}")

with open(json_path, "r", encoding="utf-8") as f:
    cache = json.load(f)

# Wenn die Datei fälschlicherweise als Liste gespeichert ist, versuche sie ins richtige Format umzuwandeln
if isinstance(cache, list):
    # Versuch: jedes Element hat evtl. ein Feld "Name" oder Schlüssel als Name - best effort
    try:
        cache = {entry["Name"]: entry for entry in cache if "Name" in entry}
    except Exception:
        # fallback: leere dict, damit Skript nicht abstürzt
        cache = {}

# ---------- Sammle eindeutige Typen und Attacken ----------
type_set = set()
attack_name_set = set()
evolution_methods_set = set()

for pokemon_name, pdata in cache.items():
    # Typen
    typen = pdata.get("Typen") or []
    for t in typen:
        if t:
            type_set.add(t)

    # Attacken - traverse attacken-Kategorien
    attacks = pdata.get("Attacken", {}) or {}
    for category, items in attacks.items():
        for atk in items:
            # manche Einträge sind einfache strings oder dicts
            if isinstance(atk, dict):
                name = atk.get("Name")
            else:
                name = str(atk)
            if name:
                attack_name_set.add(name)

    # Evolutionen - methode strings sammeln
    for evo in pdata.get("Entwicklungen", []) or []:
        m = evo.get("Methode")
        if m:
            evolution_methods_set.add(m)

# Deterministische ID-Zuweisung (sortiert für Reproduzierbarkeit)
type_list = sorted(type_set)
attack_list = sorted(attack_name_set)
method_list = sorted(evolution_methods_set)

type_map = {name: idx+1 for idx, name in enumerate(type_list)}
attack_map = {name: idx+1 for idx, name in enumerate(attack_list)}
method_map = {name: idx+1 for idx, name in enumerate(method_list)}

# ---------- SQL-Generierung ----------
lines = []
lines.append("-- Auto-generated SQL export")
lines.append("USE data_test;")
lines.append("SET FOREIGN_KEY_CHECKS = 0;")
lines.append("")

# T_Typen
lines.append("-- T_Typen")
for name, tid in type_map.items():
    lines.append(f"INSERT INTO T_Typen (Typ_ID, Typ_Name) VALUES ({tid}, {sql_str(name)});")
lines.append("")

# T_Attacken (nur Basis: ID + Name) - restliche Felder meist NULL
lines.append("-- T_Attacken (nur ID + Name; Beschreibung, Staerke, Genauigkeit, AP, Typ_ID größtenteils NULL)")
for name, aid in attack_map.items():
    lines.append(f"INSERT INTO T_Attacken (Attacken_ID, Name, Beschreibung, Staerke, Genauigkeit, AP, Typ_ID) "
                 f"VALUES ({aid}, {sql_str(name)}, NULL, NULL, NULL, NULL, NULL);")
lines.append("")

# T_Pokemon & T_Basis_Stats & T_Pokemon_Typen
lines.append("-- T_Pokemon, T_Basis_Stats, T_Pokemon_Typen")
seen_pokemon_ids = set()
for pokemon_name, pdata in cache.items():
    raw_id = pdata.get("ID")
    pokedex_nr = extract_number_from_id(raw_id)
    if pokedex_nr is None:
        # überspringen, falls keine numerische ID ermittelbar
        continue
    if pokedex_nr in seen_pokemon_ids:
        # bereits erzeugt (falls mehrere Einträge mit gleicher Nummer existieren)
        pass
    else:
        seen_pokemon_ids.add(pokedex_nr)
        # T_Pokemon
        lines.append(f"INSERT INTO T_Pokemon (Pokedex_Nr, Name) VALUES ({pokedex_nr}, {sql_str(pokemon_name)});")

        # Basis Stats
        sv = pdata.get("Statuswerte") or {}
        if sv:
            kp = sv.get("KP")
            ang = sv.get("Angriff")
            ver = sv.get("Verteidigung")
            spang = sv.get("SpAngriff") or sv.get("Sp_Angriff") or sv.get("SpAngriff")
            spver = sv.get("SpVerteidigung") or sv.get("Sp_Verteidigung") or sv.get("SpVerteidigung")
            init = sv.get("Initiative")
            lines.append(
                f"INSERT INTO T_Basis_Stats (Pokedex_Nr, KP, Angriff, Verteidigung, Sp_Angriff, Sp_Verteidigung, Initiative) "
                f"VALUES ({pokedex_nr}, {sql_int_or_null(kp)}, {sql_int_or_null(ang)}, {sql_int_or_null(ver)}, "
                f"{sql_int_or_null(spang)}, {sql_int_or_null(spver)}, {sql_int_or_null(init)});"
            )
        else:
            # falls keine Statuswerte vorhanden sind, schreibe NULLs
            lines.append(
                f"INSERT INTO T_Basis_Stats (Pokedex_Nr, KP, Angriff, Verteidigung, Sp_Angriff, Sp_Verteidigung, Initiative) "
                f"VALUES ({pokedex_nr}, NULL, NULL, NULL, NULL, NULL, NULL);"
            )

        # Typen (n:m)
        for t in pdata.get("Typen", []) or []:
            tid = type_map.get(t)
            if tid:
                lines.append(f"INSERT INTO T_Pokemon_Typen (Pokedex_Nr, Typ_ID) VALUES ({pokedex_nr}, {tid});")

lines.append("")

# T_Evolutions_Methoden
lines.append("-- T_Evolutions_Methoden")
for mname, mid in method_map.items():
    # Stein_Name können wir evtl. aus einem Eintrag entnehmen: wir setzen NULL (manuell prüfen)
    lines.append(f"INSERT INTO T_Evolutions_Methoden (Methode_ID, Methoden_Name, Stein_Name) VALUES ({mid}, {sql_str(mname)}, NULL);")
lines.append("")

# T_Entwicklung
lines.append("-- T_Entwicklung")
evo_counter = 1
for pokemon_name, pdata in cache.items():
    raw_id = pdata.get("ID")
    from_nr = extract_number_from_id(raw_id)
    if from_nr is None:
        continue
    for evo in pdata.get("Entwicklungen", []) or []:
        to_raw = evo.get("ID")
        to_nr = extract_number_from_id(to_raw)
        methode = evo.get("Methode")
        mid = method_map.get(methode)
        level = evo.get("Level")
        level_sql = sql_int_or_null(level) if level is not None else "NULL"
        # Wenn to_nr None ist (z.B. "003g1"), wir extrahieren führende digits; falls immer noch None, setze NULL
        if to_nr is None:
            to_nr_sql = "NULL"
        else:
            to_nr_sql = str(to_nr)

        if mid is None:
            # Falls Methode nicht gemappt (selten), setze NULL - aber wir sollten alle Methoden gesammelt haben
            mid_sql = "NULL"
        else:
            mid_sql = str(mid)

        lines.append(
            f"INSERT INTO T_Entwicklung (Evolutions_ID, Von_Pokemon_Nr, Zu_Pokemon_Nr, Methode_ID, Level) "
            f"VALUES ({evo_counter}, {from_nr}, {to_nr_sql}, {mid_sql}, {level_sql});"
        )
        evo_counter += 1
lines.append("")

# T_Pokemon_Attacken (n:m mit zusätzlichen Attributen)
lines.append("-- T_Pokemon_Attacken")
poke_attack_counter = 1
for pokemon_name, pdata in cache.items():
    raw_id = pdata.get("ID")
    pokedex_nr = extract_number_from_id(raw_id)
    if pokedex_nr is None:
        continue

    attacks = pdata.get("Attacken", {}) or {}
    for method, items in attacks.items():
        for atk in items:
            # Standardfall: dict mit "Name" und ggf. Level, Art, Nummer
            if isinstance(atk, dict):
                name = atk.get("Name")
            else:
                name = str(atk)
            if not name:
                continue
            aid = attack_map.get(name)
            if aid is None:
                # Sollte nicht passieren, aber skippen wenn unbekannt
                continue
            erlernmethode = method  # z.B. "LevelUp", "TM", "TP", "Ei", "Tutor"
            level_val = None
            voraus = None
            if isinstance(atk, dict):
                level_val = atk.get("Level")
                # Voraussetzung versuchen: Art+Nummer (bei TM/TP)
                art = atk.get("Art")
                nummer = atk.get("Nummer")
                if art and nummer:
                    voraus = f"{art}{nummer}"
                else:
                    # evtl. andere Felder -> schlicht als Text speichern
                    # wir versuchen, falls keys vorhanden sind, diese als JSON-string zu setzen
                    if "Voraussetzung" in atk:
                        voraus = atk.get("Voraussetzung")
                    else:
                        voraus = None

            # SQL
            lines.append(
                "INSERT INTO T_Pokemon_Attacken (Pokedex_Nr, Attacken_ID, Erlernmethode, Level, Voraussetzung) "
                f"VALUES ({pokedex_nr}, {aid}, {sql_str(erlernmethode)}, {sql_int_or_null(level_val)}, {sql_str(voraus) if voraus is not None else 'NULL'});"
            )
            poke_attack_counter += 1

lines.append("")
lines.append("SET FOREIGN_KEY_CHECKS = 1;")
lines.append("")

# ---------- Schreibe Datei ----------
with open(OUTPUT_SQL, "w", encoding="utf-8") as out:
    out.write("\n".join(lines))

# Zusammenfassung / Hinweise
summary_lines = []
summary_lines.append(f"Export fertig: {OUTPUT_SQL}")
summary_lines.append(f"Anzahl Typen: {len(type_map)}")
summary_lines.append(f"Anzahl Attacken (unique names): {len(attack_map)}")
summary_lines.append(f"Anzahl Pokemon (unique Pokedex_Nr): {len(seen_pokemon_ids)}")
summary_lines.append("")
summary_lines.append("Hinweise: Einige Tabellen/Felder werden nicht vollautomatisch befüllt (siehe README unten).")

print("\n".join(summary_lines))

# ---------- Liste der unvollständigen Daten (für den Nutzer) ----------
incomplete = [
    "T_Attacken: Felder Beschreibung, Staerke, Genauigkeit, AP, Typ_ID -> größtenteils NULL (keine Info im Cache)",
    "T_Evolutions_Methoden: Stein_Name oft NULL (Item-Feld in JSON kann fehlen oder unstrukturiert sein)",
    "T_Entwicklung: Manche 'Zu_Pokemon_Nr' können spezielle Form-IDs enthalten (z.B. '003g1'). Script extrahiert führende Ziffern, prüfe manuell.",
    "T_Pokemon_Attacken: Voraussetzung ist meist nur 'TMxx'/'TPxx' oder NULL; keine vollständige Quellen-/Generationsinfo.",
    "Generell: Attacken-Typ, Stärke, Genauigkeit, AP sind nicht im pokemon_knowledge_cache.json enthalten -> müssen aus Angriffs-Quelle (z.B. attack_cache oder Web) ergänzt werden.",
    "Fundorte, Fähigkeiten-Details, EiGruppen, Fangrate etc. werden nicht in die SQL-Tabellen importiert (nur Basis-Tabellen)."
]

print("\nUnvollständige / manuell zu überprüfende Einträge:")
for li in incomplete:
    print(" - " + li)

print("\nFertig. Öffne die Datei und prüfe die Inserts; passe dann fehlende Felder manuell an.")
