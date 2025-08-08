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
            return match.group(1)
        print(f"❌ Kein Wikitext für {pokemon_name} gefunden.")
    except Exception as e:
        print(f"❌ Fehler beim Abrufen von {pokemon_name}: {e}")
    return None


def extract_value(text: str, key: str) -> Optional[str]:
    match = re.search(rf"\|{key}=([^\|\n}]+)", text)
    if match:
        return match.group(1).strip().replace("[[", "").replace("]]", "")
    return None


def extract_statuswerte(text: str) -> Dict[str, int]:
    werte = {
        "KP": "kp_basis",
        "Angriff": "angr_basis",
        "Verteidigung": "vert_basis",
        "SpAngriff": "spangr_basis",
        "SpVerteidigung": "spvert_basis",
        "Initiative": "init_basis"
    }
    result = {}
    for name, key in werte.items():
        val = extract_value(text, key)
        if val and val.isdigit():
            result[name] = int(val)
    return result


def extract_entwicklungen(text: str) -> Dict[str, str]:
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
    typ1 = extract_value(text, "Typ")
    typ2 = extract_value(text, "Typ2")
    return [t for t in [typ1, typ2] if t]


def extract_faehigkeiten(text: str) -> Dict[str, List[str] | str]:
    f1 = extract_value(text, "Fähigkeit")
    f2 = extract_value(text, "Fähigkeit2")
    vf = extract_value(text, "VF")
    return {
        "Faehigkeiten": [f for f in [f1, f2] if f],
        "VersteckteFaehigkeit": vf or ""
    }


def extract_fangrate(text: str) -> int:
    val = extract_value(text, "Fangrate")
    return int(val) if val and val.isdigit() else 0


def extract_eigruppen(text: str) -> List[str]:
    g1 = extract_value(text, "Ei-Gruppe")
    g2 = extract_value(text, "Ei-Gruppe2")
    return [g for g in [g1, g2] if g]


def build_pokemon_entry(pokemon_name: str) -> Optional[Dict]:
    text = fetch_raw_wikitext(pokemon_name)
    if not text:
        return None

    typen = extract_typen(text)
    entwicklungen = extract_entwicklungen(text)
    faehigkeiten = extract_faehigkeiten(text)
    statuswerte = extract_statuswerte(text)
    fangrate = extract_fangrate(text)
    eigruppen = extract_eigruppen(text)

    return {
        "Typen": typen,
        "Entwicklungen": entwicklungen,
        "Faehigkeiten": faehigkeiten["Faehigkeiten"],
        "VersteckteFaehigkeit": faehigkeiten["VersteckteFaehigkeit"],
        "Statuswerte": statuswerte,
        "Fangrate": fangrate,
        "Fundorte": {},  # wird später ergänzt
        "Attacken": {
            "LevelUp": [],
            "TM": [],
            "Ei": [],
            "Tutor": []
        },
        "EiGruppen": eigruppen
    }


def save_to_cache(pokemon_name: str, data: Dict, filename: str = "pokemon_cache.json"):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            cache = json.load(f)
    else:
        cache = {}

    cache[pokemon_name] = data

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    print(f"✅ {pokemon_name} wurde gespeichert.")


def main():
    poki_name = "Maxax"
    entry = build_pokemon_entry(poki_name)
    if entry:
        save_to_cache(poki_name, entry)


if __name__ == "__main__":
    main()
