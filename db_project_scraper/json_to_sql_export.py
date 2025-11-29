#!/usr/bin/env python3
"""
json_to_sql_export.py

Exportiert JSON-Caches in SQL-Inserts passend zum aktuellen DDL.
UPDATES:
- Filtert Attacken ohne AP (AP is None) komplett raus.
- Gibt gedroppte Attacken in der Konsole aus.
- Verhindert FK-Fehler, indem gedroppte Attacken auch bei Pokemon ignoriert werden.
- Dedupliziert Pokemon_Attacken Einträge.
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

# --- Wiki Cleanup Helpers ---
def remove_wiki_markup(s: str) -> str:
    if not s:
        return s
    s = re.sub(r'\[\[([^|\]]*\|)?([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[Datei:[^\]]+\]\]', '', s)
    s = re.sub(r'\{\{[^}]+\}\}', '', s)
    s = s.replace('&amp;nbsp;', ' ').replace('&lt;br /&gt;', ' ')
    s = re.sub(r'&[^;\s]+;', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

_non_kanto_tokens = [
    'Alola','Galar','Paldea','Hisui','Kalos','Hoenn','Sinnoh',
    'PLA','PLZA','SW','SH','OR','AS','LGP','LGE', 'Gen.', 'Spielgeneration'
]

_stone_re = re.compile(
    r'\b(Blattstein|Donnerstein|Eisstein|Feuerstein|Mondstein|Sonnenstein|Wasserstein'
    r'|Schwarzaugit|Galarnuss(?:-Kranz|-Reif)?|King-Stein|Magmaisierer|Metallmantel'
    r'|Schützer|Stromisierer|Upgrade|Drachenschuppe|Dubiosdisc|Ewigstein'
    r'|Glücksrauch|Lahmrauch|Schrägrauch)\b',
    flags=re.IGNORECASE
)

def classify_and_shorten(raw: str):
    if not raw:
        return False, None, None
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
        if not lv_match:
            lv_match = re.search(r'\b(ab|bei)\s*level\s*(\d{1,3})', lc)
            lv = lv_match.group(2) if lv_match else None
        else:
            lv = lv_match.group(1)

        method_short = f'ab Level {lv}' if lv else 'Levelaufstieg'
        if 'nachts' in lc: method_short += ' (nachts)'
        elif 'tags' in lc: method_short += ' (tagsüber)'
        return True, method_short, None

    if 'tausch' in lc:
        item = _stone_re.search(cleaned)
        if item: return True, 'nach Tausch (Item)', item.group(1)
        return True, 'nach Tausch', None

    if 'zucht' in lc or 'ei' in lc: return True, 'schlüpft bei Zucht', None

    short = cleaned.split('*')[0].strip()
    short = (short[:60] + '...') if len(short) > 60 else short
    if not short: return False, None, None
    return True, short, None


# ---------------- paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_POKEMON = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "pokemon_knowledge_cache.json"))
JSON_ATTACKS = os.path.abspath(os.path.join(BASE_DIR, "..", "information_storage", "attack_cache.json"))
OUTPUT_SQL = os.path.abspath(os.path.join(BASE_DIR, "pokemon_export.sql"))

GEN1_TYPES = {
    "Normal","Feuer","Wasser","Elektro","Pflanze","Eis",
    "Kampf","Gift","Boden","Flug","Psycho","Käfer",
    "Gestein","Geist","Drache"
}
FALLBACK_TYPE = "None"

# ---------------- load JSONs ----------------
if not os.path.exists(JSON_POKEMON):
    JSON_POKEMON = "pokemon_knowledge_cache.json"

pokemon_cache = {}
try:
    with open(JSON_POKEMON, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        if isinstance(data, list):
            pokemon_cache = {entry["Name"]: entry for entry in data if "Name" in entry}
        else:
            pokemon_cache = data
except FileNotFoundError:
    print(f"Error: {JSON_POKEMON} not found.")
    exit(1)

attack_cache = {}
if os.path.exists(JSON_ATTACKS):
    with open(JSON_ATTACKS, "r", encoding="utf-8") as fh:
        data = json.load(fh)
        if isinstance(data, list):
            attack_cache = {entry["Name"]: entry for entry in data if "Name" in entry}
        else:
            attack_cache = data

# ---------------- Processing Data ----------------

type_set = set()
attack_name_set = set()
seen_pokemon_ids = set()
all_lernmethoden_set = set()

for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue
    seen_pokemon_ids.add(pid)

    for t in (pdata.get("Typen") or []):
        if t and t in GEN1_TYPES:
            type_set.add(t)

    attacks = pdata.get("Attacken", {}) or {}
    for method, items in attacks.items():
        if method:
            all_lernmethoden_set.add(method)
        for atk in items:
            name = atk.get("Name") if isinstance(atk, dict) else str(atk)
            if name:
                attack_name_set.add(name)

for aname, ainfo in attack_cache.items():
    at = ainfo.get("Typ")
    if at and at in GEN1_TYPES:
        type_set.add(at)
    attack_name_set.add(aname)

type_set.add(FALLBACK_TYPE)
type_list = sorted(type_set)
attack_list = sorted(attack_name_set)
lernmethoden_list = sorted(all_lernmethoden_set)

# --- Prepare Rows ---

# T_Typen
t_typen_rows = [[sql_str_escape(t)] for t in type_list]

# T_Lernmethoden
t_lernmethoden_rows = [[sql_str_escape(m)] for m in lernmethoden_list]

# T_Attacken (Jetzt mit AP-Filter)
t_attacken_rows = []
dropped_attacks = []        # Liste für die Konsole
valid_attacks_set = set()   # Set für FK-Checks

for name in attack_list:
    ainfo = attack_cache.get(name, {})
    typ = ainfo.get("Typ")
    typ_name = typ if (typ in type_list and typ in GEN1_TYPES) else FALLBACK_TYPE

    raw_ap = ainfo.get("AP")

    # NEU: Check ob AP vorhanden ist
    if raw_ap is None:
        dropped_attacks.append(name)
        continue # Drop this attack, do NOT add to rows

    # Wenn wir hier sind, ist die Attacke gültig
    valid_attacks_set.add(name)

    t_attacken_rows.append([
        sql_str_escape(name),
        sql_int_or_null(ainfo.get("Stärke") or ainfo.get("Staerke")),
        sql_int_or_null(ainfo.get("Genauigkeit")),
        sql_int_or_null(raw_ap),
        sql_str_escape(typ_name)
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
method_map = {}
method_entries = []
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

        if to_nr is None or not (1 <= to_nr <= 151):
            continue

        m_raw = evo.get("Methode")
        if not m_raw:
            continue
        keep, m_short, stein = classify_and_shorten(m_raw)
        if not keep:
            continue

        key = (m_short, stein)
        if key not in method_map:
            method_map[key] = len(method_map) + 1
            method_entries.append(key)

        mid = method_map[key]
        level = evo.get("Level")

        t_entwicklung_rows.append([
            str(evo_counter),
            str(from_nr),
            str(to_nr),
            str(mid),
            sql_int_or_null(level)
        ])
        evo_counter += 1

t_methods_rows = []
for (m_short, stein), mid in zip(method_entries, range(1, len(method_entries)+1)):
    t_methods_rows.append([str(mid), sql_str_escape(m_short), sql_str_escape(stein)])


# T_Pokemon_Attacken
t_pokemon_attack_rows = []
seen_pokatk = set()

for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue

    attacks = pdata.get("Attacken", {}) or {}
    for method, items in attacks.items():
        for atk in items:
            name = atk.get("Name") if isinstance(atk, dict) else str(atk)
            if not name:
                continue

            # WICHTIG: Wenn die Attacke wegen fehlender AP gedropped wurde,
            # darf sie hier NICHT rein (sonst FK Error)
            if name not in valid_attacks_set:
                continue

            # Deduplizierung
            unique_key = (pid, name, method)
            if unique_key in seen_pokatk:
                continue

            seen_pokatk.add(unique_key)

            level_val = atk.get("Level") if isinstance(atk, dict) else None
            voraus = None
            if isinstance(atk, dict):
                art = atk.get("Art")
                nummer = atk.get("Nummer")
                if art and nummer:
                    voraus = f"{art}{nummer}"
                elif atk.get("Voraussetzung"):
                    voraus = atk.get("Voraussetzung")

            t_pokemon_attack_rows.append([
                str(pid),
                sql_str_escape(name),
                sql_str_escape(method),
                sql_int_or_null(level_val),
                sql_str_escape(voraus)
            ])


# ---------------- write SQL ----------------
with open(OUTPUT_SQL, "w", encoding="utf-8") as out:
    out.write("-- Auto-generated SQL export\n")
    out.write("USE data_test;\n")
    out.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

    write_batch_insert(out, "T_Typen", ["Typ_Name"], t_typen_rows)
    write_batch_insert(out, "T_Lernmethoden", ["Erlernmethode"], t_lernmethoden_rows)
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
                       t_methods_rows)
    write_batch_insert(out, "T_Entwicklung",
                       ["Evolutions_ID", "Von_Pokemon_Nr", "Zu_Pokemon_Nr", "Methode_ID", "Level"],
                       t_entwicklung_rows)
    write_batch_insert(out, "T_Pokemon_Attacken",
                       ["Pokedex_Nr", "Attacke_Name", "Erlernmethode", "Level", "Voraussetzung"],
                       t_pokemon_attack_rows)

    out.write("SET FOREIGN_KEY_CHECKS = 1;\n")

# ---------------- Reporting ----------------
print(f"Export fertig: {OUTPUT_SQL}")
print(f"Gültige Attacken exportiert: {len(t_attacken_rows)}")
print(f"Verknüpfte Pokemon-Attacken: {len(t_pokemon_attack_rows)}")

if dropped_attacks:
    print(f"\n--- ACHTUNG: {len(dropped_attacks)} Attacken wurden wegen fehlender AP (NULL) ignoriert ---")
    print("Diese Attacken fehlen auch in T_Pokemon_Attacken, um FK-Fehler zu vermeiden:")
    for d in sorted(dropped_attacks):
        print(f" - {d}")
else:
    print("\nKeine Attacken wegen fehlender AP gedropped.")