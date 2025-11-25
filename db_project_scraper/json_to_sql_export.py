#!/usr/bin/env python3
"""
json_to_sql_export.py

Exportiert JSON-Caches in SQL-Inserts passend zum aktuellen DDL:
- T_Typen (Typ_Name)
- T_Attacken (Attacke_Name, Staerke, Genauigkeit, AP, Typ_Name)
- T_Pokemon (Pokedex_Nr, Pokemon_Name)
- T_Basis_Stats
- T_Pokemon_Typen (Pokedex_Nr, Typ_Name)
- T_Evolutions_Methoden
- T_Entwicklung
- T_Pokemon_Attacken (Pokedex_Nr, Attacke_Name, Erlernmethode, Level, Voraussetzung)

Eigenschaften:
- Batch INSERTs (mehrere VALUES in einer INSERT)
- Überschreibt die Output-Datei (erst leert, dann schreibt)
- Beschränkt auf Gen 1 (Pokedex 1-151)
- Nutzt attack_cache, wenn möglich, um Attacken-Felder zu füllen
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
    s = s.replace("'", "''")
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
    """rows already contain SQL literals (strings like "'foo'", "NULL", "123")"""
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

# Fallback type used when an attack's type is missing or outside GEN1
FALLBACK_TYPE = "None"

# ---------------- load JSONs ----------------
if not os.path.exists(JSON_POKEMON):
    raise FileNotFoundError(f"pokemon cache not found: {JSON_POKEMON}")
with open(JSON_POKEMON, "r", encoding="utf-8") as fh:
    pokemon_cache = json.load(fh)
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
    # typen (nur Gen1-Typen)
    for t in (pdata.get("Typen") or []):
        if t:
            # accept even if slightly malformed; keep as-is but only add if gen1
            if t in GEN1_TYPES:
                type_set.add(t)
            else:
                # keep uncommon types out of gen1 typeset (they will be fallbacked)
                pass
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

# also collect types from attack_cache (but only add GEN1 types)
for aname, ainfo in (attack_cache.items() if attack_cache else {}):
    at = ainfo.get("Typ")
    if at and at in GEN1_TYPES:
        type_set.add(at)
    # ensure attack name present too
    attack_name_set.add(aname)

# ensure fallback type exists in the set (so we can reference it in T_Attacken)
type_set.add(FALLBACK_TYPE)

# sort and prepare
type_list = sorted(type_set)
# for counting/printing
attack_list = sorted(attack_name_set)

# ---------------- prepare SQL rows (adapted to new DDL) ----------------

# T_Typen: single column Typ_Name
t_typen_rows = []
for tname in type_list:
    t_typen_rows.append([sql_str_escape(tname)])

# T_Attacken: (Attacke_Name, Staerke, Genauigkeit, AP, Typ_Name)
t_attacken_rows = []
for name in attack_list:
    ainfo = attack_cache.get(name, {}) if attack_cache else {}
    typ = ainfo.get("Typ")
    # prefer GEN1 type; otherwise fallback
    typ_name = typ if (typ in type_list and typ in GEN1_TYPES) else FALLBACK_TYPE
    staerke = ainfo.get("Stärke") or ainfo.get("Staerke")
    genau = ainfo.get("Genauigkeit")
    ap = ainfo.get("AP")
    t_attacken_rows.append([
        sql_str_escape(name),
        sql_int_or_null(staerke),
        sql_int_or_null(genau),
        sql_int_or_null(ap),
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
    # Typen (use type name strings, only gen1 types)
    for t in (pdata.get("Typen") or []):
        if t and t in type_list:
            t_pokemon_typen_rows.append([str(pid), sql_str_escape(t)])

import re

# --- Hilfsfunktionen (falls du sql_str_escape bereits hast, behalte sie, sonst einfach übernehmen) ---
def remove_wiki_markup(s: str) -> str:
    """Rudimentäre Entfernung/Wandlung von Wiki-Markups:
       [[Ziel|Anzeigename]] -> Anzeigename, [[Ziel]] -> Ziel, HTML Entities -> lesbar."""
    if not s:
        return s
    # Pipe-Auswahl: [[A|B]] -> B
    s = re.sub(r'\[\[([^|\]]*\|)?([^\]]+)\]\]', r'\2', s)
    # Entferne Dateiverweise etc.
    s = re.sub(r'\[\[Datei:[^\]]+\]\]', '', s)
    # Entferne {{...}} Vorlagen (nur grob)
    s = re.sub(r'\{\{[^}]+\}\}', '', s)
    # HTML Entities &lt; &gt; &amp;nbsp; -> lesbar
    s = s.replace('&amp;nbsp;', ' ').replace('&lt;br /&gt;', ' ').replace('&lt;br /&gt;', ' ')
    s = re.sub(r'&[^;\s]+;', ' ', s)
    # Mehrfachspaces reduzieren
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# Liste von Regionstokens, die NICHT zur 1. Gen (Kanto) gehören -> Filter
_non_kanto_tokens = [
    'Alola','Galar','Paldea','Hisui','Kalos','Hoenn','Sinnoh',
    # Abkürzungen / Spielcodes, die auf neuere Spiele hinweisen
    'PLA','PLZA','SW','SH','OR','AS','LGP','LGE',
    # explizite Hinweise auf Generationen >1
    'Gen.', 'Spielgeneration'  # (falls du statt regionsbasiert noch Generationen filtern willst)
]

# Regex, das typische "Stein"-/Item-Namen erkennt (deutsch, einfache Form)
_stone_re = re.compile(
    r'\b(Blattstein|Donnerstein|Eisstein|Feuerstein|Mondstein|Sonnenstein|Wasserstein'
    r'|Schwarzaugit|Galarnuss(?:-Kranz|-Reif)?|King-Stein|Magmaisierer|Metallmantel'
    r'|Schützer|Stromisierer|Upgrade|Drachenschuppe|Dubiosdisc|Ewigstein'
    r'|Glücksrauch|Lahmrauch|Schrägrauch)\b',
    flags=re.IGNORECASE
)

# Kürzungs-/Klassifizierungslogik
def classify_and_shorten(raw: str):
    """
    Nimmt die lange Methode (raw) und gibt zurück:
      (keep: bool, method_short: str or None, stein_name: str or None)
    Regeln:
      - Wenn Region außerhalb 1.Genomy erwähnt -> drop (keep False)
      - Wenn 'Form' erwähnt -> drop (keep False)
      - Wenn Stein/Item erkannt -> stein_name gesetzt, method_short in Form 'Stein anwenden' oder 'Item anwenden'
      - Sonst heuristische Kürzung (Levelaufstieg, nach Tausch, schlüpft bei Zucht, etc.)
    """
    if not raw:
        return False, None, None

    cleaned = remove_wiki_markup(raw)

    # Filter: Erwähnung von "Form" (ambigue Formen) -> raus
    if re.search(r'\bForm\b', cleaned, flags=re.IGNORECASE):
        return False, None, None

    # Filter: Regions-/Spielhinweise außerhalb Gen1 -> raus
    for tok in _non_kanto_tokens:
        if tok.lower() in cleaned.lower():
            return False, None, None

    # Suche Stein/Item
    m = _stone_re.search(cleaned)
    if m:
        stein = m.group(1)
        stein = stein.strip()
        # Normalisiere Schreibweise (z.B. einheitliche Großschreibung)
        stein = stein[0].upper() + stein[1:]
        # Methoden-Text: kurz und treffsicher
        if stein.lower().endswith('stein'):
            method_short = 'Stein anwenden'
        else:
            method_short = 'Item anwenden'
        return True, method_short, stein

    # Heuristiken für andere Fälle (Level, Tausch, Zucht, Kampf, Wettbewerb, etc.)
    lc = cleaned.lower()

    # Levelaufstiege (ggf. mit nacht/tag)
    if 'level' in lc or 'ab level' in lc or re.search(r'\bab \[?\[?Level', raw, flags=re.IGNORECASE):
        # versuche Levelzahl zu extrahieren
        lv_match = re.search(r'ab\s+\[\[Level\]\].*?(\d{1,3})', raw)
        if not lv_match:
            lv_match = re.search(r'\b(ab|bei)\s*level\s*(\d{1,3})', lc)
            if lv_match:
                lv = lv_match.group(2)
            else:
                lv = None
        else:
            lv = lv_match.group(1)
        zeit = None
        if 'nachts' in lc:
            zeit = ' (nachts)'
        elif 'tagsüber' in lc or 'tags' in lc:
            zeit = ' (tagsüber)'
        if lv:
            method_short = f'ab Level {lv}'
        else:
            method_short = 'Levelaufstieg'
        if zeit:
            method_short += zeit
        return True, method_short, None

    # Tausch
    if 'tausch' in lc:
        # wenn Item erwähnt => nach Tausch (Item)
        item = _stone_re.search(cleaned)
        if item:
            return True, 'nach Tausch (Item)', item.group(1)
        return True, 'nach Tausch', None

    # Zucht / Ei
    if 'zucht' in lc or 'ei' in lc:
        return True, 'schlüpft bei Zucht', None

    # Kampf / Gigadynamax / Mega
    if 'gigadynamax' in lc or 'gigadynamax' in cleaned.lower():
        return True, 'Gigadynamax im Kampf', None
    if 'mega-entwicklung' in lc or 'mega' in lc and 'entwicklung' in lc:
        return True, 'Mega-Entwicklung im Kampf', None

    # Wettbewerb / Kostümwahl
    if 'wettbewerb' in lc or 'kostümwahl' in lc:
        return True, 'Kostümwahl (Wettbewerb)', None

    # einfache Zahlen-bedingung (z.B. "nach 20 Einsätzen")
    match_after = re.search(r'nach\s+(\d+)\s+einsätzen', lc)
    if match_after:
        return True, f'nach {match_after.group(1)} Einsätzen', None

    # Fallback: kurze, bereinigte Anfangsphrase (max 60 Zeichen)
    short = cleaned.split('*')[0].strip()
    short = (short[:60] + '...') if len(short) > 60 else short
    # Wenn der Shorttext leer ist, verwerfen
    if not short:
        return False, None, None
    return True, short, None

# --- Integration in deinen bestehenden Block ---
# (ersetze das alte method_set-Extraktionsstück durch das Folgende)

method_map = {}   # key: (method_short, stein_name) -> id
method_entries = []  # Liste der Tupel in definierter Reihenfolge

for pname, pdata in pokemon_cache.items():
    raw_id = pdata.get("ID")
    pid = extract_number_from_id(raw_id)
    if pid is None or not (1 <= pid <= 151):
        continue
    for evo in (pdata.get("Entwicklungen") or []):
        m_raw = evo.get("Methode")
        if not m_raw:
            continue
        keep, m_short, stein = classify_and_shorten(m_raw)
        if not keep:
            # gefiltert: entweder Form-bezogen oder Region außerhalb 1.Gen
            continue
        key = (m_short, stein)
        if key not in method_map:
            method_map[key] = len(method_map) + 1
            method_entries.append(key)

# Jetzt method_map enthält IDs, basierend auf der gekürzten Methode + Stein

# Erzeuge t_methods_rows (wie in deinem ursprünglichen Skript)
t_methods_rows = []
for (m_short, stein), mid in zip(method_entries, range(1, len(method_entries)+1)):
    # sql_str_escape bleibt wie in deinem Skript
    stein_sql = f"'{stein}'" if stein is not None else "NULL"
    t_methods_rows.append([str(mid), sql_str_escape(m_short), stein_sql])

# Beim Erzeugen der T_Entwicklung Zeilen nutze die neue map:
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
        m_raw = evo.get("Methode")
        if not m_raw:
            continue
        keep, m_short, stein = classify_and_shorten(m_raw)
        if not keep:
            continue
        key = (m_short, stein)
        mid = method_map.get(key)
        level = evo.get("Level")
        from_sql = str(from_nr)
        to_sql = str(to_nr) if (to_nr is not None and 1 <= to_nr <= 151) else "NULL"
        mid_sql = str(mid) if mid is not None else "NULL"
        level_sql = sql_int_or_null(level) if level is not None else "NULL"
        t_entwicklung_rows.append([str(evo_counter), from_sql, to_sql, mid_sql, level_sql])
        evo_counter += 1

# T_Pokemon_Attacken (Pokedex_Nr, Attacke_Name, Erlernmethode, Level, Voraussetzung)
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
            erlernmethode = method
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
                sql_str_escape(erlernmethode),
                sql_int_or_null(level_val),
                sql_str_escape(voraus) if voraus is not None else "NULL"
            ])

# ---------------- write SQL file (overwrite) ----------------
with open(OUTPUT_SQL, "w", encoding="utf-8") as out:
    out.write("-- Auto-generated SQL export (überschreibt diese Datei)\n")
    out.write("USE data_test;\n")
    out.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

    # T_Typen (only Typ_Name)
    write_batch_insert(out, "T_Typen", ["Typ_Name"], t_typen_rows, batch_size=200)

    # T_Attacken (Attacke_Name, Staerke, Genauigkeit, AP, Typ_Name)
    write_batch_insert(out, "T_Attacken",
                       ["Attacke_Name", "Staerke", "Genauigkeit", "AP", "Typ_Name"],
                       t_attacken_rows, batch_size=200)

    # T_Pokemon (Pokedex_Nr, Pokemon_Name)
    write_batch_insert(out, "T_Pokemon", ["Pokedex_Nr", "Pokemon_Name"], t_pokemon_rows, batch_size=200)

    # T_Basis_Stats
    write_batch_insert(out, "T_Basis_Stats",
                       ["Pokedex_Nr", "KP", "Angriff", "Verteidigung", "Sp_Angriff", "Sp_Verteidigung", "Initiative"],
                       t_basis_rows, batch_size=200)

    # T_Pokemon_Typen (Pokedex_Nr, Typ_Name)
    write_batch_insert(out, "T_Pokemon_Typen", ["Pokedex_Nr", "Typ_Name"], t_pokemon_typen_rows, batch_size=500)

    # T_Evolutions_Methoden (Methode_ID, Methoden_Name, Stein_Name)
    write_batch_insert(out, "T_Evolutions_Methoden", ["Methode_ID", "Methoden_Name", "Stein_Name"], t_methods_rows, batch_size=200)

    # T_Entwicklung (Evolutions_ID, Von_Pokemon_Nr, Zu_Pokemon_Nr, Methode_ID, Level)
    write_batch_insert(out, "T_Entwicklung", ["Evolutions_ID", "Von_Pokemon_Nr", "Zu_Pokemon_Nr", "Methode_ID", "Level"], t_entwicklung_rows, batch_size=200)

    # T_Pokemon_Attacken (Pokedex_Nr, Attacke_Name, Erlernmethode, Level, Voraussetzung)
    write_batch_insert(out, "T_Pokemon_Attacken", ["Pokedex_Nr", "Attacke_Name", "Erlernmethode", "Level", "Voraussetzung"], t_pokemon_attack_rows, batch_size=500)

    out.write("SET FOREIGN_KEY_CHECKS = 1;\n")

# ---------------- summary ----------------
print("Export fertig:", OUTPUT_SQL)
print(f"Anzahl Typen (eingefügt): {len(type_list)}")
print(f"Anzahl Attacken (unique names): {len(attack_list)}")
print(f"Anzahl Pokemon (Gen1, unique Pokedex_Nr): {len(seen_pokemon_ids)}")
print(f"Anzahl T_Pokemon_Attacken entries: {len(t_pokemon_attack_rows)}")
print(f"Anzahl Entwicklungen (Evolutions rows): {len(t_entwicklung_rows)}")

incomplete = [
    "T_Attacken: Beschreibung ist NULL (nicht im attack_cache).",
    "T_Attacken: Falls attack_cache unvollständig ist, fehlen Staerke/Genauigkeit/AP für manche Attacken - bitte attack_cache ergänzen.",
    "T_Evolutions_Methoden: Stein_Name wird nicht automatisch extrahierbar -> manuell prüfen.",
    "T_Entwicklung: 'Zu_Pokemon_Nr' aus Form-IDs (z.B. '003g1') wurde zu NULL gemappt; falls separate Form-Einträge gewünscht, manuell nacharbeiten.",
    "T_Pokemon_Attacken: 'Voraussetzung' ist rudimentär (z.B. 'TM11' oder NULL). Generation / Quelle / exakte Lernbedingungen fehlen.",
    "Allgemein: Fundorte, Fähigkeiten-Beschreibungen, Ei-Gruppen, Fangrate werden nicht in den Zieltabellen übernommen.",
    "Nur Gen1 (1-151) wurden exportiert - alle späteren Generationen ignoriert."
]

print("\nUnvollständige / manuell zu prüfende Einträge:")
for i in incomplete:
    print(" - " + i)

print("\nHinweis: Prüfe die Datei 'pokemon_export.sql' auf Typenzuordnungen und Attacken-Daten. Wenn du möchtest, kann ich das Script erweitern, um die Attacken-Types konsistenter zu behandeln (z.B. alle Attacken-Typen in T_Typen übernehmen, auch wenn sie nicht Gen1).")
