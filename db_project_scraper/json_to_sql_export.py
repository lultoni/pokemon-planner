#!/usr/bin/env python3
"""
json_to_sql_export_v2.py

Exportiert JSON-Caches in SQL-Inserts passend zum NEUEN DDL (Normalisierte Lernmethoden).

Änderungen zum DDL:
- T_Lernmethoden ist jetzt komplex (ID, Art, Level, Voraussetzung).
- T_Pokemon_Attacken referenziert Lernmethode_ID.
- AP NULL Check bleibt aktiv.
- Deduplizierung bleibt aktiv.
"""

import json
import os
import re

# ---------------- helpers ----------------
def sql_str_escape(s):
    """Return SQL literal for strings (or NULL)"""
    if s is None:
        return "NULL"
    s = str(s)
    s = s.replace("'", "''") # Escape single quotes for SQL
    return f"'{s}'"

def sql_int_or_null(v):
    if v is None:
        return "NULL"
    try:
        return str(int(v))
    except Exception:
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
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def write_batch_insert(f, table, columns, rows, batch_size=500):
    if not rows:
        return
    col_str = ", ".join(columns)
    for block in chunks(rows, batch_size):
        values_str = ",\n".join("(" + ", ".join(row) + ")" for row in block)
        f.write(f"INSERT INTO {table} ({col_str}) VALUES\n{values_str};\n\n")

# --- Wiki Cleanup / Parsing Helpers ---
def remove_wiki_markup(s: str) -> str:
    if not s: return s
    s = re.sub(r'\[\[([^|\]]*\|)?([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[Datei:[^\]]+\]\]', '', s)
    s = re.sub(r'\{\{[^}]+\}\}', '', s)
    s = s.replace('&amp;nbsp;', ' ').replace('&lt;br /&gt;', ' ')
    s = re.sub(r'&[^;\s]+;', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

_stone_re = re.compile(
    r'\b(Blattstein|Donnerstein|Eisstein|Feuerstein|Mondstein|Sonnenstein|Wasserstein'
    r'|Schwarzaugit|Galarnuss(?:-Kranz|-Reif)?|King-Stein|Magmaisierer|Metallmantel'
    r'|Schützer|Stromisierer|Upgrade|Drachenschuppe|Dubiosdisc|Ewigstein'
    r'|Glücksrauch|Lahmrauch|Schrägrauch)\b', flags=re.IGNORECASE
)

_non_kanto_tokens = ['Alola','Galar','Paldea','Hisui','Kalos','Hoenn','Sinnoh','PLA','PLZA','SW','SH','OR','AS','LGP','LGE', 'Gen.', 'Spielgeneration']

def classify_and_shorten_evo(raw: str):
    """Logik für Entwicklungs-Methoden (nicht Lernmethoden!)"""
    if not raw: return False, None, None
    cleaned = remove_wiki_markup(raw)

    if re.search(r'\bForm\b', cleaned, flags=re.IGNORECASE): return False, None, None
    for tok in _non_kanto_tokens:
        if tok.lower() in cleaned.lower(): return False, None, None

    m = _stone_re.search(cleaned)
    if m:
        stein = m.group(1).strip()
        stein = stein[0].upper() + stein[1:]
        method_short = 'Stein anwenden' if 'stein' in stein.lower() else 'Item anwenden'
        return True, method_short, stein

    lc = cleaned.lower()
    if 'level' in lc or 'ab level' in lc:
        lv_match = re.search(r'ab\s+\[\[Level\]\].*?(\d{1,3})', raw)
        lv = lv_match.group(1) if lv_match else (re.search(r'\b(ab|bei)\s*level\s*(\d{1,3})', lc).group(2) if re.search(r'\b(ab|bei)\s*level\s*(\d{1,3})', lc) else None)
        method_short = f'ab Level {lv}' if lv else 'Levelaufstieg'
        if 'nachts' in lc: method_short += ' (nachts)'
        elif 'tags' in lc: method_short += ' (tagsüber)'
        return True, method_short, None

    if 'tausch' in lc:
        item = _stone_re.search(cleaned)
        if item: return True, 'nach Tausch (Item)', item.group(1)
        return True, 'nach Tausch', None

    if 'zucht' in lc or 'ei' in lc: return True, 'schlüpft bei Zucht', None

    short = cleaned.split('*')[0].strip()[:60]
    if not short: return False, None, None
    return True, short, None

def normalize_attack_method(raw_method_key, atk_obj):
    """
    Analysiert den Key im JSON (z.B. "Level", "TM/VM") und das Objekt.
    Gibt zurück: (Art, Level, Voraussetzung)
    """
    art = raw_method_key
    level = None
    voraussetzung = None

    # Normalisierung der Art
    raw_lower = raw_method_key.lower()
    if 'level' in raw_lower:
        art = 'Level-Up'
    elif 'tm' in raw_lower or 'vm' in raw_lower:
        art = 'TM/VM'
    elif 'zucht' in raw_lower or 'ei' in raw_lower:
        art = 'Zucht'
    elif 'tutor' in raw_lower:
        art = 'Tutor'

    # Daten extrahieren wenn atk_obj ein Dict ist
    if isinstance(atk_obj, dict):
        # Level extrahieren
        if atk_obj.get("Level"):
            try:
                level = int(atk_obj.get("Level"))
            except:
                pass

        # Voraussetzung extrahieren (z.B. TM Nummer)
        if atk_obj.get("Art") and atk_obj.get("Nummer"):
            voraussetzung = f"{atk_obj.get('Art')}{atk_obj.get('Nummer')}"
        elif atk_obj.get("Voraussetzung"):
            voraussetzung = atk_obj.get("Voraussetzung")

    return art, level, voraussetzung

# ---------------- paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_POKEMON = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "pokemon_knowledge_cache.json"))
JSON_ATTACKS = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "attack_cache.json"))
OUTPUT_SQL = os.path.abspath(os.path.join(BASE_DIR, "dml_pokemon_script.sql"))

GEN1_TYPES = {
    "Normal","Feuer","Wasser","Elektro","Pflanze","Eis",
    "Kampf","Gift","Boden","Flug","Psycho","Käfer",
    "Gestein","Geist","Drache"
}
FALLBACK_TYPE = "None"

# ---------------- load JSONs ----------------
if not os.path.exists(JSON_POKEMON):
    JSON_POKEMON = "pokemon_knowledge_cache.json" # Fallback

pokemon_cache = {}
try:
    with open(JSON_POKEMON, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        pokemon_cache = {entry["Name"]: entry for entry in data if "Name" in entry} if isinstance(data, list) else data
except FileNotFoundError:
    print(f"Error: {JSON_POKEMON} not found.")
    exit(1)

attack_cache = {}
if os.path.exists(JSON_ATTACKS):
    with open(JSON_ATTACKS, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        attack_cache = {entry["Name"]: entry for entry in data if "Name" in entry} if isinstance(data, list) else data

# ---------------- DATA PROCESSING ----------------

type_set = set()
attack_name_set = set()
seen_pokemon_ids = set()

# 1. Initiale Sammlung (Typen, Attackennamen)
for pname, pdata in pokemon_cache.items():
    pid = extract_number_from_id(pdata.get("ID"))
    if pid is None or not (1 <= pid <= 151): continue
    seen_pokemon_ids.add(pid)

    for t in (pdata.get("Typen") or []):
        if t and t in GEN1_TYPES: type_set.add(t)

    for method, items in (pdata.get("Attacken") or {}).items():
        for atk in items:
            name = atk.get("Name") if isinstance(atk, dict) else str(atk)
            if name: attack_name_set.add(name)

for aname, ainfo in attack_cache.items():
    if ainfo.get("Typ") in GEN1_TYPES: type_set.add(ainfo.get("Typ"))
    attack_name_set.add(aname)

type_set.add(FALLBACK_TYPE)
type_list = sorted(type_set)
attack_list = sorted(attack_name_set)

# ---------------- PREPARE T_ATTACKEN (Check AP) ----------------
t_attacken_rows = []
dropped_attacks = []
valid_attacks_set = set()

for name in attack_list:
    ainfo = attack_cache.get(name, {})
    typ = ainfo.get("Typ")
    typ_name = typ if (typ in type_list and typ in GEN1_TYPES) else FALLBACK_TYPE
    raw_ap = ainfo.get("AP")

    if raw_ap is None:
        dropped_attacks.append(name)
        continue

    valid_attacks_set.add(name)
    t_attacken_rows.append([
        sql_str_escape(name),
        sql_int_or_null(ainfo.get("Stärke") or ainfo.get("Staerke")),
        sql_int_or_null(ainfo.get("Genauigkeit")),
        sql_int_or_null(raw_ap),
        sql_str_escape(typ_name)
    ])

# ---------------- PREPARE T_LERNMETHODEN (Complex) ----------------
# Wir müssen alle Kombinationen aus (Art, Level, Voraussetzung) finden,
# eine ID zuweisen und merken.

lernmethode_map = {} # Key: (Art, Level, Voraussetzung) -> ID
next_lm_id = 1
t_lernmethoden_rows = []

# Scanne ALLE Pokemon nach Lernmethoden
for pname, pdata in pokemon_cache.items():
    pid = extract_number_from_id(pdata.get("ID"))
    if pid is None or not (1 <= pid <= 151): continue

    attacks = pdata.get("Attacken", {}) or {}
    for method_key, items in attacks.items():
        for atk in items:
            name = atk.get("Name") if isinstance(atk, dict) else str(atk)

            # Wenn Attacke ungültig (kein AP), brauchen wir die Methode hierfür auch nicht merken
            if not name or name not in valid_attacks_set:
                continue

            # Analysiere Methode
            art, level, voraus = normalize_attack_method(method_key, atk)

            # Tuple für Unique Check
            lm_key = (art, level, voraus)

            if lm_key not in lernmethode_map:
                lernmethode_map[lm_key] = next_lm_id
                t_lernmethoden_rows.append([
                    str(next_lm_id),
                    sql_str_escape(art),
                    sql_int_or_null(level),
                    sql_str_escape(voraus)
                ])
                next_lm_id += 1

# ---------------- PREPARE OTHER TABLES ----------------

t_typen_rows = [[sql_str_escape(t)] for t in type_list]

t_pokemon_rows = []
t_basis_rows = []
t_pokemon_typen_rows = []

for pname, pdata in pokemon_cache.items():
    pid = extract_number_from_id(pdata.get("ID"))
    if pid is None or not (1 <= pid <= 151): continue

    t_pokemon_rows.append([str(pid), sql_str_escape(pname)])

    sv = pdata.get("Statuswerte") or {}
    t_basis_rows.append([
        str(pid),
        sql_int_or_null(sv.get("KP")),
        sql_int_or_null(sv.get("Angriff")),
        sql_int_or_null(sv.get("Verteidigung")),
        sql_int_or_null(sv.get("SpAngriff") or sv.get("Sp_Angriff")),
        sql_int_or_null(sv.get("SpVerteidigung") or sv.get("Sp_Verteidigung")),
        sql_int_or_null(sv.get("Initiative"))
    ])

    for t in (pdata.get("Typen") or []):
        if t and t in type_list:
            t_pokemon_typen_rows.append([str(pid), sql_str_escape(t)])

# T_Evolutions_Methoden & T_Entwicklung
evo_method_map = {}
evo_method_entries = []
t_entwicklung_rows = []
evo_counter = 1

for pname, pdata in pokemon_cache.items():
    from_nr = extract_number_from_id(pdata.get("ID"))
    if from_nr is None or not (1 <= from_nr <= 151): continue

    for evo in (pdata.get("Entwicklungen") or []):
        to_nr = extract_number_from_id(evo.get("ID"))
        if to_nr is None or not (1 <= to_nr <= 151): continue # Drop if target null

        m_raw = evo.get("Methode")
        keep, m_short, stein = classify_and_shorten_evo(m_raw)
        if not keep: continue

        key = (m_short, stein)
        if key not in evo_method_map:
            evo_method_map[key] = len(evo_method_map) + 1
            evo_method_entries.append(key)

        mid = evo_method_map[key]
        t_entwicklung_rows.append([
            str(evo_counter), str(from_nr), str(to_nr), str(mid), sql_int_or_null(evo.get("Level"))
        ])
        evo_counter += 1

t_evo_methods_rows = []
for (m_short, stein), mid in zip(evo_method_entries, range(1, len(evo_method_entries)+1)):
    t_evo_methods_rows.append([str(mid), sql_str_escape(m_short), sql_str_escape(stein)])

# ---------------- PREPARE T_POKEMON_ATTACKEN ----------------
# Nutzt jetzt Lernmethode_ID und das valid_attacks_set
t_pokemon_attack_rows = []
seen_pokatk = set() # (pid, attack_name, lernmethode_id)

for pname, pdata in pokemon_cache.items():
    pid = extract_number_from_id(pdata.get("ID"))
    if pid is None or not (1 <= pid <= 151): continue

    attacks = pdata.get("Attacken", {}) or {}
    for method_key, items in attacks.items():
        for atk in items:
            name = atk.get("Name") if isinstance(atk, dict) else str(atk)

            # Check AP (dropped?)
            if not name or name not in valid_attacks_set:
                continue

            # Ermittle die ID für diese spezifische Art/Level/Voraussetzung Kombination
            art, level, voraus = normalize_attack_method(method_key, atk)
            lm_key = (art, level, voraus)

            lm_id = lernmethode_map.get(lm_key)

            # Safety Check: Sollte eigentlich immer da sein, da wir oben gescannt haben
            if lm_id is None:
                print(f"WARNUNG: Lernmethode nicht gefunden für {pname} -> {name}")
                continue

            # Deduplizierung (Pokedex_Nr, Attacke_Name, Lernmethode_ID)
            unique_key = (pid, name, lm_id)
            if unique_key in seen_pokatk:
                continue

            seen_pokatk.add(unique_key)

            t_pokemon_attack_rows.append([
                str(pid),
                sql_str_escape(name),
                str(lm_id)
            ])


# ---------------- WRITE SQL ----------------
with open(OUTPUT_SQL, "w", encoding="utf-8") as out:
    out.write("-- Auto-generated SQL Insert Script\n")
    out.write("USE data_test;\n")
    out.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

    write_batch_insert(out, "T_Typen", ["Typ_Name"], t_typen_rows)

    # NEU: Lernmethoden mit Details
    write_batch_insert(out, "T_Lernmethoden",
                       ["Lernmethode_ID", "Art", "Level", "Voraussetzung"],
                       t_lernmethoden_rows)

    write_batch_insert(out, "T_Attacken",
                       ["Attacke_Name", "Staerke", "Genauigkeit", "AP", "Typ_Name"],
                       t_attacken_rows)

    write_batch_insert(out, "T_Pokemon", ["Pokedex_Nr", "Pokemon_Name"], t_pokemon_rows)

    write_batch_insert(out, "T_Basis_Stats",
                       ["Pokedex_Nr", "KP", "Angriff", "Verteidigung", "Sp_Angriff", "Sp_Verteidigung", "Initiative"],
                       t_basis_rows)

    write_batch_insert(out, "T_Pokemon_Typen", ["Pokedex_Nr", "Typ_Name"], t_pokemon_typen_rows)

    write_batch_insert(out, "T_Evolutions_Methoden",
                       ["Methode_ID", "Methoden_Name", "Stein_Name"],
                       t_evo_methods_rows)

    write_batch_insert(out, "T_Entwicklung",
                       ["Evolutions_ID", "Von_Pokemon_Nr", "Zu_Pokemon_Nr", "Methode_ID", "Level"],
                       t_entwicklung_rows)

    # NEU: Nur noch Referenz auf ID
    write_batch_insert(out, "T_Pokemon_Attacken",
                       ["Pokedex_Nr", "Attacke_Name", "Lernmethode_ID"],
                       t_pokemon_attack_rows)

    out.write("SET FOREIGN_KEY_CHECKS = 1;\n")

# ---------------- REPORT ----------------
print(f"Export fertig: {OUTPUT_SQL}")
print(f"Generierte Lernmethoden-Kombinationen: {len(t_lernmethoden_rows)}")
print(f"Pokemon Attacken Verknüpfungen: {len(t_pokemon_attack_rows)}")

if dropped_attacks:
    print(f"\n--- ACHTUNG: {len(dropped_attacks)} Attacken wurden wegen fehlender AP (NULL) ignoriert ---")
    for d in sorted(dropped_attacks):
        print(f" - {d}")