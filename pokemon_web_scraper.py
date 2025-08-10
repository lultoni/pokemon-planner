from __future__ import annotations

import requests
import re
import json
import os
from typing import List, Optional, Dict


def fetch_raw_wikitext(pokemon_name: str) -> Optional[str]:
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}&action=edit"
    try:
        response = requests.get(url)
        response.raise_for_status()

        match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
        if match:
            wikitext = match.group(1)

            # Suche nach der Überschrift "Typ-Schwächen"
            typ_schwaechen_pattern = r"=== Typ-Schwächen ==="
            typ_schwaechen_match = re.search(typ_schwaechen_pattern, wikitext)

            if typ_schwaechen_match:
                # Schneide den Text ab, bevor die Überschrift "Typ-Schwächen" beginnt
                cut_wikitext = wikitext[:typ_schwaechen_match.start()]
                return cut_wikitext

            print("⚠️ Wikitext gefunden, aber keine 'Typ-Schwächen'-Sektion. Rückgabe des vollständigen Textes.")
            return wikitext

        print(f"❌ Kein Wikitext für {pokemon_name} gefunden.")
    except Exception as e:
        print(f"❌ Fehler beim Abrufen von {pokemon_name}: {e}")
    return None


def extract_value(text: str, key: str) -> Optional[str]:
    escaped_key = re.escape(key)
    pattern = rf"\|{escaped_key}(?!_)=([^|\n}}]+)"

    match = re.search(pattern, text)
    if match:
        raw_value = match.group(1)
        cleaned_value = raw_value.strip().replace("[[", "").replace("]]", "")
        return cleaned_value
    return None


def extract_statuswerte(text: str, pokemon_name: str) -> Dict[str, int]:
    """
    Extrahiert Statuswerte für das angegebene Pokémon.
    Unterstützt Standardform, Regionsform oder nur einen Block ohne Namenszeile.
    """
    werte_keys = {
        "KP": "kp_basis",
        "Angriff": "angr_basis",
        "Verteidigung": "vert_basis",
        "SpAngriff": "spangr_basis",
        "SpVerteidigung": "spvert_basis",
        "Initiative": "init_basis"
    }

    # Region erkennen (Format: "Region-Name")
    region = None
    base_name = pokemon_name
    if "-" in pokemon_name:
        parts = pokemon_name.split("-", 1)
        if len(parts) == 2:
            region, base_name = parts

    # Passenden Abschnitt suchen
    section_pattern = None
    if region:
        section_pattern = rf";{region}-{base_name}\s*\n\{{\{{Statuswerte.*?\n\}}\}}"
    else:
        section_pattern = rf";{base_name}\s*\n\{{\{{Statuswerte.*?\n\}}\}}"

    match = re.search(section_pattern, text, re.DOTALL)

    # Fallback: erster Statuswerte-Block im Text
    if not match:
        match = re.search(r"\{\{Statuswerte.*?\n\}\}", text, re.DOTALL)

    if not match:
        return {}  # Kein Block gefunden

    section_text = match.group(0)

    # Werte extrahieren
    result = {}
    for name, key in werte_keys.items():
        val = extract_value(section_text, key)
        if val and val.isdigit():
            result[name] = int(val)

    return result


def extract_entwicklungen(text: str) -> Dict[str, str]: # todo test
    entwicklungen = {}
    match1 = re.search(r'Stufe1\|(\d+)\|.*?\[\[([^\]]+)\]\]', text)
    match2 = re.search(r'Stufe2\|(\d+)\|.*?Level[^0-9]*(\d+)', text)
    match3 = re.search(r'Stufe3\|(\d+)\|.*?Level[^0-9]*(\d+)', text)

    if match1:
        entwicklungen["Vorentwicklung1"] = match1.group(2)
    if match2:
        entwicklungen["Vorentwicklung2"] = "Sharfax"  # Pokéwiki gibt den Namen nicht nochmal an
        entwicklungen["Level1"] = int(match2.group(2))
    if match3:
        entwicklungen["Level2"] = int(match3.group(2))

    return entwicklungen


def extract_typen(text: str) -> List[str]:
    def clean(val: Optional[str]) -> Optional[str]:
        if val:
            return val.strip().replace("[[", "").replace("]]", "")
        return None

    form_zusatz = extract_value(text, "Typ2Zusatz_a") or extract_value(text, "TypZusatz_a")

    if form_zusatz and "Galar" in form_zusatz:
        form_typ = clean(extract_value(text, "Typ_a"))
        form_typ2 = clean(extract_value(text, "Typ2_a"))
        return [t for t in [form_typ, form_typ2] if t]

    typ1 = clean(extract_value(text, "Typ"))
    typ2 = clean(extract_value(text, "Typ2"))
    return [t for t in [typ1, typ2] if t]


def extract_faehigkeiten(text: str) -> Dict[str, List[str] | str]: # todo test
    f1 = extract_value(text, "Fähigkeit")
    f2 = extract_value(text, "Fähigkeit2")
    vf = extract_value(text, "VF")
    return {
        "Faehigkeiten": [f for f in [f1, f2] if f],
        "VersteckteFaehigkeit": vf or ""
    }


def extract_fangrate(text: str) -> int: # todo test
    val = extract_value(text, "Fangrate")
    return int(val) if val and val.isdigit() else 0


def extract_eigruppen(text: str) -> List[str]: # todo test
    g1 = extract_value(text, "Ei-Gruppe")
    g2 = extract_value(text, "Ei-Gruppe2")
    return [g for g in [g1, g2] if g]


def build_pokemon_entry(pokemon_name: str) -> Optional[Dict]: # todo test
    text = fetch_raw_wikitext(pokemon_name)
    if not text:
        return None

    typen = extract_typen(text)
    entwicklungen = extract_entwicklungen(text)
    faehigkeiten = extract_faehigkeiten(text)
    statuswerte = extract_statuswerte(text, pokemon_name)
    fangrate = extract_fangrate(text)
    eigruppen = extract_eigruppen(text)

    return {
        "Typen": typen,
        "Entwicklungen": entwicklungen,
        "Faehigkeiten": faehigkeiten["Faehigkeiten"],
        "VersteckteFaehigkeit": faehigkeiten["VersteckteFaehigkeit"],
        "Statuswerte": statuswerte,
        "Fangrate": fangrate,
        "Fundorte": {}, # todo append with function
        "Attacken": { # todo append with function
            "LevelUp": [],
            "TM": [],
            "Ei": [],
            "Tutor": []
        },
        "EiGruppen": eigruppen
    }


def save_to_cache(pokemon_name: str, data: Dict, filename: str = "information_storage/pokemon_knowledge_cache.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            cache = json.load(f)
    else:
        cache = {}

    cache[pokemon_name] = data

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)
    print(f"✅ {pokemon_name} wurde gespeichert.")


def main():
    poki_name = "Zigzachs"
    entry = build_pokemon_entry(poki_name)
    if entry:
        save_to_cache(poki_name, entry)


if __name__ == "__main__":
    main()