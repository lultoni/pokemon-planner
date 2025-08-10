"""
attack_scraper.py

Sammelt die Wikicode-Seiten von Attacken von Pokéwiki (Edit-Ansicht)
und speichert strukturierte (so gut es geht) Daten in
global_infos.ATTACK_CACHE_FILE_PATH (JSON).

Features:
- Angriffsnamen als Kommandozeilenargumente oder aus einer Datei einlesen
- Optional: alle Attacken aus dem Pokemon-Cache (global_infos.POKEMON_CACHE_FILE_PATH)
- Versucht, vorhandene Funktion `extract_structured_attacks` zu verwenden, sonst Fallback-Parser

Benutzung:
python attack_scraper.py Flamethrower Donnerschlag
python attack_scraper.py --file attacks.txt
python attack_scraper.py --from-pokemon-cache

"""
from __future__ import annotations

import argparse
import json
import os
import re
import requests
import sys
from typing import Dict, List, Optional

# Importiere globale Pfade
try:
    import global_infos
except Exception as e:
    print("Fehler: Modul 'global_infos' konnte nicht importiert werden. Stelle sicher, dass es im PYTHONPATH ist.")
    raise

# Versuche, vorhandene Parser-Funktionen zu verwenden (falls Teil des Projekts)
try:
    # falls extract_structured_attacks in demselben Projekt definiert ist
    from pokemon_web_scraper import extract_structured_attacks  # type: ignore
except Exception:
    extract_structured_attacks = None  # Fallback nutzen


def normalize_title(name: str) -> str:
    """Wandelt einen Display-Namen zu dem Titel um, den Pokéwiki in der URL erwartet.
    Beispiele: Räume Leerzeichen in '_' um, keine weiteren Änderungen (Pokéwiki nutzt meist Unterstriche).
    """
    # Pokéwiki benutzt oft Unterstriche bei URLs und Umlaute bleiben (werden urlencoded automatisch von requests)
    return name.replace(" ", "_")


def fetch_attack_page_wikitext(attack_name: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """Lädt die Edit-Ansicht einer Attacke und extrahiert den Inhalt des Textareas (wpTextbox1).
    Gibt None zurück, wenn etwas schiefgeht.
    """
    sess = session or requests.Session()
    title = normalize_title(attack_name)
    url = f"https://www.pokewiki.de/index.php?title={title}&action=edit"
    try:
        r = sess.get(url, timeout=15)
        r.raise_for_status()
        match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', r.text, re.DOTALL)
        if match:
            wikitext = match.group(1)
            return wikitext
        print(f"❌ Kein Wikitext für Attacke '{attack_name}' gefunden (Seite geladen).")
    except Exception as e:
        print(f"❌ Fehler beim Abrufen von Attacke '{attack_name}': {e}")
    return None


# Fallback-Parser: versucht einige typische Felder aus der Attackenseite herauszuziehen
FIELD_PATTERNS = {
    "Typ": re.compile(r"\|\s*[Tt]yp\s*=\s*([^\n\|}]+)"),
    "Kategorie": re.compile(r"\|\s*[Kk]ategorie\s*=\s*([^\n\|}]+)"),
    "Stärke": re.compile(r"\|\s*(?:Stärke|Schaden|Power)\s*=\s*([^\n\|}]+)"),
    "Genauigkeit": re.compile(r"\|\s*[Gg]enauigkeit\s*=\s*([^\n\|}]+)"),
    "AP": re.compile(r"\|\s*AP\s*=\s*([^\n\|}]+)"),
    "Priority": re.compile(r"\|\s*Priority\s*=\s*([^\n\|}]+)"),
    "Beschreibung": re.compile(r"(?:<small>|)\s*([^\n\r]{10,300})\s*(?:</small>|)"),
}


def simple_extract_fields(wikitext: str) -> Dict[str, Optional[str]]:
    """Extrahiert mit heuristischen Regex-Feldern einige nützliche Informationen.
    Liefert ein Dict mit den extrahierten Feldern (None wenn nicht gefunden) und dem Rohtext.
    """
    data: Dict[str, Optional[str]] = {}
    for key, pat in FIELD_PATTERNS.items():
        m = pat.search(wikitext)
        data[key] = m.group(1).strip() if m else None
    data["Rohtext"] = wikitext
    return data


def build_attack_entry(attack_name: str, session: Optional[requests.Session] = None) -> Optional[Dict]:
    """Erstellt den zu speichernden Eintrag für eine Attacke.
    Wenn eine projektinterne Funktion `extract_structured_attacks` vorhanden ist, wird sie (falls kompatibel) verwendet.
    Ansonsten wird ein einfacher Fallback-Parser genutzt und der komplette Rohtext gespeichert.
    """
    text = fetch_attack_page_wikitext(attack_name, session=session)
    if not text:
        return None

    # Falls bereits ein Projektparser existiert und eine Funktion bereitsteht, versuche diese zu nutzen
    if extract_structured_attacks:
        try:
            parsed = extract_structured_attacks(text)
            # Wenn die Funktion eine Liste zurückgibt, nehmen wir das erste Element oder packen die Liste als 'Parsed'
            if isinstance(parsed, list):
                return {"Name": attack_name, "Parsed": parsed, "Rohtext": text}
            return {"Name": attack_name, "Parsed": parsed, "Rohtext": text}
        except Exception as e:
            print(f"⚠️ Fehler beim Verwenden von 'extract_structured_attacks': {e} — falle zurück auf simplen Parser.")

    # Fallback: einfache Feld-Extraktion
    extracted = simple_extract_fields(text)
    entry = {
        "Name": attack_name,
        "Typ": extracted.get("Typ"),
        "Kategorie": extracted.get("Kategorie"),
        "Stärke": extracted.get("Stärke"),
        "Genauigkeit": extracted.get("Genauigkeit"),
        "AP": extracted.get("AP"),
        "Priority": extracted.get("Priority"),
        "Beschreibung_snippet": extracted.get("Beschreibung"),
        "Rohtext": extracted.get("Rohtext"),
    }
    return entry


def save_attack_to_cache(attack_name: str, data: Dict, filename: str = None):
    if filename is None:
        filename = global_infos.ATTACK_CACHE_FILE_PATH

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    else:
        cache = {}

    cache[attack_name] = data

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    print(f"✅ {attack_name} wurde in {filename} gespeichert.")


def load_attacks_from_file(path: str) -> List[str]:
    if not os.path.exists(path):
        print(f"Datei '{path}' nicht gefunden.")
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines()]
    # Entferne Kommentare/Leere Zeilen
    attacks = [ln for ln in lines if ln and not ln.startswith("#")]
    return attacks


def load_attacks_from_pokemon_cache(pokemon_cache_path: str) -> List[str]:
    """Liest alle Attackennamen aus dem Pokemon-Cache (falls vorhanden).
    Erwartet, dass die Struktur dem in build_pokemon_entry zurückgegebenen Dict entspricht
    und unter dem Schlüssel 'Attacken' eine Liste mit Attackennamen oder Attacken-Objekten steht.
    """
    if not os.path.exists(pokemon_cache_path):
        print(f"Pokemon-Cache '{pokemon_cache_path}' nicht gefunden.")
        return []
    try:
        with open(pokemon_cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception as e:
        print(f"Fehler beim Laden des Pokemon-Caches: {e}")
        return []

    attacks_set = set()
    for pname, pdata in cache.items():
        attacks = pdata.get("Attacken")
        if not attacks:
            continue
        # Attacken können Strings oder Objekte sein
        for a in attacks:
            if isinstance(a, str):
                attacks_set.add(a)
            elif isinstance(a, dict):
                # falls das Objekt einen Namen enthält
                name = a.get("Name") or a.get("Bezeichnung")
                if name:
                    attacks_set.add(name)
    return sorted(attacks_set)


def main(argv: Optional[List[str]] = None):
    ap = argparse.ArgumentParser(description="Scrape Attacken-Wikitext von Pokéwiki und speichern in JSON-Cache.")
    ap.add_argument("attacks", nargs="*", help="Namen der Attacken (z.B. Flamethrower), Leerzeichen bitte in Anführungszeichen oder mit Unterstrich")
    ap.add_argument("--file", "-f", help="Datei mit Attackennamen, eine pro Zeile")
    ap.add_argument("--from-pokemon-cache", action="store_true", help="Alle Attacken aus dem Pokemon-Cache laden")
    ap.add_argument("--cache-file", help="Ziel-JSON-Datei (überschreibt global_infos.ATTACK_CACHE_FILE_PATH)")
    args = ap.parse_args(argv)

    target_file = args.cache_file or global_infos.ATTACK_CACHE_FILE_PATH

    attacks: List[str] = []
    if args.file:
        attacks.extend(load_attacks_from_file(args.file))

    if args.from_pokemon_cache:
        attacks.extend(load_attacks_from_pokemon_cache(global_infos.POKEMON_CACHE_FILE_PATH))

    if args.attacks:
        attacks.extend(args.attacks)

    attacks = [a for a in attacks if a]  # filter
    if not attacks:
        print("Keine Attacken angegeben. Nutze --help für Optionen.")
        return

    sess = requests.Session()
    for a in attacks:
        print(f"--- Verarbeite: {a}")
        entry = build_attack_entry(a, session=sess)
        if entry:
            save_attack_to_cache(a, entry, filename=target_file)
        else:
            print(f"⚠️ Konnte Eintrag für Attacke '{a}' nicht erstellen.")


if __name__ == '__main__':
    main()
