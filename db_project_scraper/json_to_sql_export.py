#!/usr/bin/env python3
"""
json_to_sql_export.py

Erzeugt pokemon_export.sql aus:
- information_storage/pokemon_knowledge_cache.json
- information_storage/attack_cache.json

Eigenschaften:
- Batch INSERTs (mehrere VALUES in einer INSERT)
- Überschreibt die Output-Datei (erst leert, dann schreibt)
- Beschränkt auf Gen 1 (Pokedex 1-151)
- Nutzt attack_cache, wenn möglich, um T_Attacken-Felder zu füllen
"""

import json
import os
import re
from math import ceil

# ---------------- helpers ----------------
def sql_str_escape(s):
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
        # versuche zu casten float->int
        try:
            return str(int(float(v)))
        except Exception:
            return "NULL"

def extract_number_from_id(id_str):
    if id_str is None:
        return None
    s = str(id_str)
    m = re.match(r'0*([0-9]+)', s)
    if m:
        return int(m.group(1))
    m2 = re.search(r'([0-9]+)', s)
    if m2:
        return int(m2.group(1))
    return None

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def write_batch_insert(f, table, columns, rows, batch_size=500):
    """
    rows: list of lists of SQL-literals (already escaped using helpers) (e.g. ["1", "'Bulbasaur'", "NULL"])
    columns: list of column names
    writes multiple INSERT ... VALUES (...),(...);
    """
    if not rows:
        return
    col_str = ", ".join(columns)
    for block in chunks(rows, batch_size):
        values_str = ",\n".join("(" + ", ".join(row) + ")" for row in block)
        f.write(f"INSERT INTO {table} ({col_str}) VALUES\n{values_str};\n\n")

# ---------------- paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_POKEMON = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "pokemon_knowledge_cache.json"))
JSON_ATTACKS = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "attack_cache.json"))
OUTPUT_SQL = os.path.abspath(os.path.join(BASE_DIR, "pokemon_export.sql"))

# ---------------- Gen1 types (canonical list) ----------------
GEN1_TYPES = {
    "Normal","Feuer","Wasser","Elektro","Pflanze","Eis",
    "Kampf","Gift","Boden","Flug","Psycho","Käfer",
    "Gestein","Geist","Drache"
}
# (Steel/Dark/Fairy existieren nicht in Gen1; wir ignorieren sie)

# ---------------- load JSONs ----------------
if not os.path.exists(JSON_POKEMON):
    raise FileNotFoundError(f"pokemon cache not found: {JSON_POKEMON}")
with open(JSON_POKEMON, "r", encoding="utf-8") as fh:
    pokemon_cache = json.load(fh)
# fallback if it's a list
if isinstance(pokemon_cache, list):
    try:
        pokemon_cache = {entry["Name"]: entry for entry in pokemon_cache if "Name" in entry}
    except Exception:
        pokemon_cache = {}

attack_cache = {}
if os.path.exists(JSON_ATTACKS):
    with open(JSON_ATTACKS, "r", encoding="utf-8") as fh:
        attack_cache = json.load(fh)
    if isinstance(attack_cache, list):
        try:
            attack_cache = {entry["Name"]: entry for entry in attack_cache if "Name" in entry}
        except Exception:
            attack_cache = {}
else:
    print("Warnung: attack_cache nicht gefunden, T_Attacken wird nur mit Namen gefüllt.")

# ---------------- collect types and attacks (only from gen1 pokemon) ----------------
type_set = set()
attack_name_set = set()

seen_pokemon_ids = set()
for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue  # nur gen1
    seen_pokemon_ids.add(pid)
    # typen
    for t in (pdata.get("Typen") or []):
        if t and t in GEN1_TYPES:
            type_set.add(t)
    # attacks
    attacks = pdata.get("Attacken", {}) or {}
    for cat, items in attacks.items():
        for atk in items:
            name = None
            if isinstance(atk, dict):
                name = atk.get("Name")
            else:
                name = str(atk)
            if name:
                attack_name_set.add(name)

# auch Typs aus attack_cache hinzufügen, aber nur Gen1-Typen
for aname, ainfo in (attack_cache.items() if attack_cache else {}):
    at = ainfo.get("Typ")
    if at and at in GEN1_TYPES:
        type_set.add(at)
    # ensure attack name present too (we'll add attack entries from cache as well)
    attack_name_set.add(aname)

# sort and map to IDs
type_list = sorted(type_set)
type_map = {name: i+1 for i, name in enumerate(type_list)}

# build attack list combining names we saw (deterministic order)
attack_list = sorted(attack_name_set)
attack_map = {name: i+1 for i, name in enumerate(attack_list)}

# ---------------- prepare SQL rows ----------------
t_typen_rows = []
for name, tid in type_map.items():
    t_typen_rows.append([str(tid), sql_str_escape(name)])

# T_Attacken: include fields (Attacken_ID, Name, Beschreibung, Staerke, Genauigkeit, AP, Typ_ID)
t_attacken_rows = []
for name, aid in attack_map.items():
    ainfo = attack_cache.get(name, {})
    typ = ainfo.get("Typ")
    staerke = ainfo.get("Stärke") or ainfo.get("Staerke")
    genau = ainfo.get("Genauigkeit")
    ap = ainfo.get("AP")
    besch = None  # nicht vorhanden im attack_cache
    typ_id = type_map.get(typ) if typ in type_map else None
    t_attacken_rows.append([
        str(aid),
        sql_str_escape(name),
        "NULL",  # Beschreibung
        sql_int_or_null(staerke),
        sql_int_or_null(genau),
        sql_int_or_null(ap),
        str(typ_id) if typ_id is not None else "NULL"
    ])

# T_Pokemon, T_Basis_Stats, T_Pokemon_Typen
t_pokemon_rows = []
t_basis_rows = []
t_pokemon_typen_rows = []

for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue
    # T_Pokemon
    t_pokemon_rows.append([str(pid), sql_str_escape(pname)])
    # Basis stats
    sv = pdata.get("Statuswerte") or {}
    kp = sv.get("KP")
    ang = sv.get("Angriff")
    ver = sv.get("Verteidigung")
    spang = sv.get("SpAngriff") or sv.get("Sp_Angriff") or sv.get("SpAngriff")
    spver = sv.get("SpVerteidigung") or sv.get("Sp_Verteidigung") or sv.get("SpVerteidigung")
    init = sv.get("Initiative")
    t_basis_rows.append([
        str(pid),
        sql_int_or_null(kp),
        sql_int_or_null(ang),
        sql_int_or_null(ver),
        sql_int_or_null(spang),
        sql_int_or_null(spver),
        sql_int_or_null(init)
    ])
    # Typen
    for t in (pdata.get("Typen") or []):
        if t and t in type_map:
            t_pokemon_typen_rows.append([str(pid), str(type_map[t])])

# T_Evolutions_Methoden and T_Entwicklung
# collect unique method strings
method_set = set()
for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue
    for evo in (pdata.get("Entwicklungen") or []):
        m = evo.get("Methode")
        if m:
            method_set.add(m)

method_list = sorted(method_set)
method_map = {m: i+1 for i, m in enumerate(method_list)}

t_methods_rows = []
for m, mid in method_map.items():
    # Stein_Name nicht automatisch extrahierbar -> NULL
    t_methods_rows.append([str(mid), sql_str_escape(m), "NULL"])

t_entwicklung_rows = []
evo_counter = 1
for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    from_nr = extract_number_from_id(raw_id)
    if from_nr is None or not (1 <= from_nr <= 151):
        continue
    for evo in (pdata.get("Entwicklungen") or []):
        to_raw = evo.get("ID")
        to_nr = extract_number_from_id(to_raw)
        method = evo.get("Methode")
        mid = method_map.get(method)
        level = evo.get("Level")
        # map to SQL
        from_sql = str(from_nr)
        to_sql = str(to_nr) if (to_nr is not None and 1 <= to_nr <= 151) else "NULL"
        mid_sql = str(mid) if mid is not None else "NULL"
        level_sql = sql_int_or_null(level) if level is not None else "NULL"
        t_entwicklung_rows.append([str(evo_counter), from_sql, to_sql, mid_sql, level_sql])
        evo_counter += 1

# T_Pokemon_Attacken (Pokedex_Nr, Attacken_ID, Erlernmethode, Level, Voraussetzung)
t_pokemon_attack_rows = []
for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue
    attacks = pdata.get("Attacken", {}) or {}
    for method, items in attacks.items():
        for atk in items:
            if isinstance(atk, dict):
                name = atk.get("Name")
            else:
                name = str(atk)
            if not name:
                continue
            aid = attack_map.get(name)
            if aid is None:
                continue
            # Erlernmethode = method (z.B. "LevelUp", "TM", "TP", "Tutor", "Ei")
            erlernmethode = method
            level_val = atk.get("Level") if isinstance(atk, dict) else None
            voraus = None
            if isinstance(atk, dict):
                art = atk.get("Art")
                nummer = atk.get("Nummer")
                if art and nummer:
                    voraus = f"{art}{nummer}"
                # falls spezifische Voraussetzung-Felder existieren, nutze diese
                elif atk.get("Voraussetzung"):
                    voraus = atk.get("Voraussetzung")
            # build SQL row
            t_pokemon_attack_rows.append([
                str(pid),
                str(aid),
                sql_str_escape(erlernmethode),
                sql_int_or_null(level_val),
                sql_str_escape(voraus) if voraus is not None else "NULL"
            ])

# ---------------- write SQL file (overwrite) ----------------
with open(OUTPUT_SQL, "w", encoding="utf-8") as out:
    out.write("-- Auto-generated SQL export (überschreibt diese Datei)\n")
    out.write("USE data_test;\n")
    out.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

    # T_Typen
    write_batch_insert(out, "T_Typen", ["Typ_ID", "Typ_Name"], t_typen_rows, batch_size=200)

    # T_Attacken
    write_batch_insert(out, "T_Attacken",
                       ["Attacken_ID", "Name", "Beschreibung", "Staerke", "Genauigkeit", "AP", "Typ_ID"],
                       t_attacken_rows, batch_size=200)

    # T_Pokemon
    write_batch_insert(out, "T_Pokemon", ["Pokedex_Nr", "Name"], t_pokemon_rows, batch_size=200)

    # T_Basis_Stats
    write_batch_insert(out, "T_Basis_Stats",
                       ["Pokedex_Nr", "KP", "Angriff", "Verteidigung", "Sp_Angriff", "Sp_Verteidigung", "Initiative"],
                       t_basis_rows, batch_size=200)

    # T_Pokemon_Typen
    write_batch_insert(out, "T_Pokemon_Typen", ["Pokedex_Nr", "Typ_ID"], t_pokemon_typen_rows, batch_size=500)

    # T_Evolutions_Methoden
    write_batch_insert(out, "T_Evolutions_Methoden", ["Methode_ID", "Methoden_Name", "Stein_Name"], t_methods_rows, batch_size=200)

    # T_Entwicklung
    write_batch_insert(out, "T_Entwicklung", ["Evolutions_ID", "Von_Pokemon_Nr", "Zu_Pokemon_Nr", "Methode_ID", "Level"], t_entwicklung_rows, batch_size=200)

    # T_Pokemon_Attacken
    write_batch_insert(out, "T_Pokemon_Attacken", ["Pokedex_Nr", "Attacken_ID", "Erlernmethode", "Level", "Voraussetzung"], t_pokemon_attack_rows, batch_size=500)

    out.write("SET FOREIGN_KEY_CHECKS = 1;\n")

# ---------------- summary ----------------
print("Export fertig:", OUTPUT_SQL)
print(f"Anzahl Typen (Gen1 gefiltert): {len(type_map)}")
print(f"Anzahl Attacken (unique names): {len(attack_map)}")
print(f"Anzahl Pokemon (Gen1, unique Pokedex_Nr): {len(seen_pokemon_ids)}")
print(f"Anzahl T_Pokemon_Attacken entries: {len(t_pokemon_attack_rows)}")
print(f"Anzahl Entwicklungen (Evolutions rows): {len(t_entwicklung_rows)}")

# ---------------- incomplete fields (die du manuell prüfen / ergänzen musst) ----------------
incomplete = [
    "T_Attacken: Beschreibung ist NULL (nicht im attack_cache).",
    "T_Attacken: Manche Attacken-Typen können nicht in GEN1_TYPES auftreten (z.B. Steel/Dark/Fairy) -> geprüft werden.",
    "T_Attacken: Falls attack_cache unvollständig ist, fehlen Staerke/Genauigkeit/AP für manche Attacken - bitte attack_cache ergänzen.",
    "T_Evolutions_Methoden: Stein_Name wird nicht automatisch extrahiert (Item-Felder unstrukturiert) -> manuell prüfen.",
    "T_Entwicklung: 'Zu_Pokemon_Nr' aus Form-IDs (z.B. '003g1') wurde zu NULL gemappt; falls separate Form-Einträge gewünscht, manuell nacharbeiten.",
    "T_Pokemon_Attacken: 'Voraussetzung' ist rudimentär (z.B. 'TM11' oder NULL). Generation / Quelle / exakte Lernbedingungen fehlen.",
    "Allgemein: Fundorte, Fähigkeiten-Beschreibungen, Ei-Gruppen, Fangrate werden nicht in den Zieltabellen übernommen.",
    "Nur Gen1 (1-151) wurden exportiert - alle späteren Generationen ignoriert."
]

print("\nUnvollständige / manuell zu prüfende Einträge:")
for i in incomplete:
    print(" - " + i)

print("\nHinweis: Öffne die Datei 'pokemon_export.sql' und überprüfe insbesondere Typenzuordnungen und Attacken-Daten. Wenn du möchtest, kann ich das Script erweitern, um weitere Felder aus attack_cache noch strenger zu übernehmen (z.B. Kategorie -> Beschreibung etc.).")
