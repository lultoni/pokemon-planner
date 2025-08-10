from __future__ import annotations

import argparse
import json
import os
import re
import requests
from typing import Dict, Optional, List, Any


def normalize_title(name: str) -> str:
    """Normalisiert einen Attackennamen für die URL."""
    return name.replace(" ", "_")


def normalize_title(title: str) -> str:
    """Normalisiert den Titel für die URL (z.B. Leerzeichen zu Unterstrich)."""
    return title.replace(' ', '_')


def fetch_attack_page_wikitext(attack_name: str, session: Optional[requests.Session] = None) -> Optional[str]:
    """
    Holt den rohen Wikitext einer Attackenseite von Pokéwiki und entfernt
    irrelevante Abschnitte wie "In Spin-offs".
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

            # --- Irrelevanten Abschnitt entfernen ---
            # Sucht nach der Überschrift "== In Spin-offs ==" und schneidet alles danach ab.
            # Der re.DOTALL-Modifikator sorgt dafür, dass "." auch Newlines matched.
            wikitext_cleaned = re.split(r'==\s*In Spin-offs\s*==', wikitext, 1, flags=re.IGNORECASE | re.DOTALL)

            # Wenn der Abschnitt gefunden wurde, nehmen wir den Teil davor.
            return wikitext_cleaned[0].strip()

        print(f"❌ Kein Wikitext für Attacke '{attack_name}' gefunden.")

    except Exception as e:
        print(f"❌ Fehler beim Abrufen von Attacke '{attack_name}': {e}")

    return None


def simple_extract_fields(wikitext: str) -> Dict[str, Any]:
    """
    Extrahiert die wichtigsten Datenfelder aus dem Wikitext einer Attacke.
    Behebt Probleme bei der Verarbeitung von Generationsangaben und Sonderzeichen.
    """
    field_patterns = {
        "Typ": re.compile(r"\|\s*[Tt]yp\s*=\s*([^\|}]+)"),
        "Kategorie": re.compile(r"\|\s*(?:Klasse|Kategorie)\s*=\s*([^\|}]+)"),
        "Stärke": re.compile(r"\|\s*(?:Stärke|Power|Schaden)\s*=\s*([^\|}]+)"),
        "Genauigkeit": re.compile(r"\|\s*[Gg]enauigkeit\s*=\s*([^\|}]+)"),
        "AP": re.compile(r"\|\s*AP\s*=\s*([^\|}]+)"),
        "Priority": re.compile(r"\|\s*Priorität\s*=\s*([^\|}]+)"),
    }

    data: Dict[str, Optional[str]] = {}

    for key, pat in field_patterns.items():
        m = pat.search(wikitext)
        if m:
            raw_value = m.group(1).strip()

            # TODO: Logik für Generationsangaben testen
            # Spezialbehandlung für Stärke und Genauigkeit, um den Wert der 8. Gen zu extrahieren.
            if key in ["Stärke", "Genauigkeit"]:
                # Sucht nach dem letzten Wert, der von "ab Gen. X" (X >= 6) eingeführt wurde
                gen_value_match = re.findall(r'(\d+)\s*\(ab Gen\. [6-9]\)', raw_value)
                if gen_value_match:
                    value = gen_value_match[-1]  # Nimm den letzten Wert
                else:
                    # Wenn keine spezifische Generationsangabe vorhanden ist, nimm den ersten Zahlwert.
                    # Dies deckt Fälle wie "20<small>+</small>" ab.
                    simple_value_match = re.search(r'^(\d+)', raw_value)
                    if simple_value_match:
                        value = simple_value_match.group(1)
                    else:
                        value = raw_value # Fallback auf den rohen Wert
            else:
                value = raw_value

            # Bereinigt den extrahierten Wert
            cleaned_value = re.sub(r'<[^>]+>', '', value)
            cleaned_value = cleaned_value.replace('&nbsp;', '').replace('&amp;', '&')
            cleaned_value = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', cleaned_value)

            data[key] = cleaned_value.strip() if cleaned_value.strip() else None
        else:
            data[key] = None

    if data.get("AP"):
        ap_match = re.search(r'(\d+)\s*\(max\.\s*(\d+)\)', data["AP"])
        if ap_match:
            data["AP"], data["AP_max"] = ap_match.group(1), ap_match.group(2)
        else:
            data["AP_max"] = None # Nur AP-Wert vorhanden
    else:
        data["AP_max"] = None

    erlernbarkeiten = []
    learn_section_match = re.search(r'==\s*Erlernbarkeit\s*==\s*(.*)', wikitext, re.DOTALL)
    if learn_section_match:
        learn_section_text = learn_section_match.group(1)
        swsh_block_match = re.search(
            r'\{\{Atk-Erlernbarkeit/Kopf\|edition=swsh.*?\}\}(.*?)(?=\{\{Atk-Erlernbarkeit/Kopf|\|\}|\Z)',
            learn_section_text,
            re.DOTALL
        )
        if swsh_block_match:
            swsh_block_text = swsh_block_match.group(1)
            pokemon_numbers = re.findall(r'\{\{Atk-Erlernbarkeit/Zeile\|(\d{3,4})', swsh_block_text)
            erlernbarkeiten = [p.strip() for p in pokemon_numbers]
    data["Erlernbarkeiten"] = erlernbarkeiten

    return data


def build_attack_entry(attack_name: str) -> Optional[Dict]:
    """Baut den kompletten Datensatz für eine Attacke."""
    text = fetch_attack_page_wikitext(attack_name)
    if not text:
        return None

    extracted = simple_extract_fields(text)
    entry = {
        "Name": attack_name,
        "Typ": extracted.get("Typ"),
        "Kategorie": extracted.get("Kategorie"),
        "Stärke": extracted.get("Stärke"),
        "Genauigkeit": extracted.get("Genauigkeit"),
        "AP": extracted.get("AP"),
        "AP_max": extracted.get("AP_max"),
        "Priority": extracted.get("Priority"),
        "Erlernbarkeiten_SWSH_DexNr": extracted.get("Erlernbarkeiten")
    }
    return entry


def save_attack_to_cache(attack_name: str, data: Dict, filename: Optional[str] = None):
    """Speichert eine Attacke im JSON-Cache."""
    if filename is None:
        try:
            import global_infos  # type: ignore
            filename = getattr(global_infos, "ATTACK_CACHE_FILE_PATH", None)
        except (ImportError, AttributeError):
            filename = None

    if filename is None:
        filename = os.path.join(os.getcwd(), "attack_cache.json")

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            cache = {}
    else:
        cache = {}

    cache[attack_name] = data
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    print(f"✅ '{attack_name}' wurde erfolgreich im Cache gespeichert.")


def get_attack(attack_name: str, filename: Optional[str] = None) -> Optional[Dict]:
    """
    Holt eine Attacke aus dem Cache oder scrapt sie bei Bedarf.
    Dies ist die primäre Zugriffsfunktion für andere Skripte.
    """
    if filename is None:
        try:
            import global_infos  # type: ignore
            filename = getattr(global_infos, "ATTACK_CACHE_FILE_PATH", None)
        except (ImportError, AttributeError):
            filename = None
    if filename is None:
        filename = os.path.join(os.getcwd(), "attack_cache.json")

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if attack_name in cache:
                print(f"ℹ️ '{attack_name}' aus dem Cache geladen.")
                return cache[attack_name]
        except (json.JSONDecodeError, IOError):
            pass  # Cache ist korrupt oder leer, wird überschrieben

    print(f"ℹ️ '{attack_name}' nicht im Cache gefunden. Starte Scraping...")
    entry = build_attack_entry(attack_name)
    if entry:
        save_attack_to_cache(attack_name, entry, filename)
    return entry


def parse_args():
    """Parst die Kommandozeilenargumente."""
    ap = argparse.ArgumentParser(description="Scrape genau EINE Attacke von Pokéwiki und speichere sie in einem JSON-Cache.")
    ap.add_argument("attack", help="Name der Attacke (z. B. 'Ränkeschmied' oder 'Mogelhieb').")
    ap.add_argument("--cache-file", help="Optionaler Pfad zur Ziel-JSON-Datei.")
    return ap.parse_args()


def main():
    """Hauptfunktion des Skripts."""
    args = parse_args()
    attack_name = args.attack.strip()
    if not attack_name:
        print("Bitte einen gültigen Attackennamen angeben.")
        return

    entry = get_attack(attack_name, args.cache_file)
    if not entry:
        print(f"⚠️ Konnte die Attacke '{attack_name}' nicht abrufen oder verarbeiten.")
    else:
        # Gib eine saubere Zusammenfassung aus
        print("\n--- Ergebnisse für:", attack_name, "---")
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("---------------------------------")


if __name__ == '__main__':
    main()