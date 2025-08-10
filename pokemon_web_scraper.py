from __future__ import annotations

import html

import requests
import re
import json
import os
from typing import List, Optional, Dict, Tuple


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
        match = re.search(r"\{\{Statuswerte.*?\n}}", text, re.DOTALL)

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


def extract_entwicklungen(text: str, id_to_name: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Extrahiert Entwicklungsstufen aus 'Zucht, Entwicklung und Formen'.
    Gibt eine Liste von Entwicklungsinfos in Reihenfolge zurück.
    """
    entwicklungen = []

    # Muster für jede Stufe
    pattern = re.compile(
        r"\{\{Zucht, Entwicklung und Formen/Stufe(?P<stufe>[123])\|(?P<id>[\d\w]+)\|Methode=(?P<methode>.*?)\}\}",
        re.DOTALL
    )

    for match in pattern.finditer(text):
        stufe = int(match.group("stufe"))
        poke_id = match.group("id")
        methode = match.group("methode").replace("\n", " ").strip()

        if id_to_name:
            name = id_to_name.get(poke_id, f"ID_{poke_id}")
        else:
            name = "None"

        # Level extrahieren
        level_match = re.search(r"Level(?:[^0-9]|&nbsp;)*(\d+)", methode)
        level = int(level_match.group(1)) if level_match else None

        # Item extrahieren (z. B. Feuerstein, Eisstein)
        item_match = re.search(r"\[\[([^\]]+stein)\]\]", methode, re.IGNORECASE)
        item = item_match.group(1) if item_match else None

        # Zeitbedingungen
        zeit_match = re.search(r"nachts|tagsüber", methode, re.IGNORECASE)
        zeit = zeit_match.group(0) if zeit_match else None

        # Region extrahieren
        region_match = re.search(r"in\s+\[\[([^\]]+)\]\]", methode)
        region = region_match.group(1) if region_match else None

        # Generation extrahieren
        gen_match = re.search(r"Gen\.\s*\{\{G\|(\d+)\}\}", methode)
        generation = int(gen_match.group(1)) if gen_match else None

        entwicklungen.append({
            "Stufe": stufe,
            "ID": poke_id,
            "Name": name,
            "Level": level,
            "Item": item,
            "Zeit": zeit,
            "Region": region,
            "Generation": generation,
            "Methode": methode
        })

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


def _parse_form_field(raw: str) -> List[Tuple[str, List[str]]]:
    """
    Zerlegt z.B.
    '[[Schneemantel]] <sup>(Alola)</sup><br>[[Schneeschauer]] <sup>(VF Alola)</sup>'
    oder 'Wutausbruch &lt;small>(Galar)&lt;/small>'
    in eine Liste von (Fähigkeitsname, [Annotationen]).
    """
    if not raw:
        return []
    s = html.unescape(raw)                       # &lt; -> < etc.
    s = re.sub(r'(?i)<br\s*/?>', '\n', s)        # <br> → newline
    parts = re.split(r'\n|\*', s)                # newline und * als Trenner
    res: List[Tuple[str, List[str]]] = []

    for p in parts:
        p = p.strip()
        if not p:
            continue

        # Name: zuerst versuchen [[Link|Anzeigename]] oder [[Name]]
        m = re.search(r'\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]', p)
        if m:
            name = m.group(2) if m.group(2) else m.group(1)
        else:
            # Plain-Text: bis zu erstem '<' oder '(' oder Ende
            name = re.split(r'\s*(?:<|\(|$)', p)[0].strip()

        # Annotations sammeln:
        annotations: List[str] = []
        # Parentheses z.B. (Galar) oder (VF Alola)
        annotations += re.findall(r'\(([^)]+)\)', p)
        # Tags wie <small>..</small> oder <sup>..</sup>
        tag_matches = re.findall(r'<(?:small|sup)[^>]*>(.*?)</(?:small|sup)>', p, flags=re.I|re.S)
        for t in tag_matches:
            tclean = t.strip().strip('() ')
            if tclean:
                annotations.append(tclean)

        # dedupe + strip
        annotations = [a.strip() for a in dict.fromkeys(annotations) if a.strip()]
        res.append((name, annotations))

    return res


def extract_faehigkeiten(text: str, pokemon_name: str) -> Dict[str, List[str] | str]:
    """
    Gibt { "Faehigkeiten": [...], "VersteckteFaehigkeit": "..." } zurück.
    Wenn pokemon_name eine Region enthält (z.B. "Galar-Zigzachs"), werden
    bevorzugt Regionen-Fähigkeiten genutzt (falls vorhanden).
    """
    # Region erkennen (z.B. "Galar" aus "Galar-Zigzachs")
    region: Optional[str] = None
    if "-" in pokemon_name:
        region = pokemon_name.split("-", 1)[0].strip()

    # Basis-Felder (extrahiert mit deinem bestehenden extract_value; unescape zur Sicherheit)
    base_f1 = extract_value(text, "Fähigkeit") or ""
    base_f2 = extract_value(text, "Fähigkeit2") or ""
    base_vf = extract_value(text, "VF") or ""
    base_f1 = html.unescape(base_f1).strip()
    base_f2 = html.unescape(base_f2).strip()
    base_vf = html.unescape(base_vf).strip()

    # Form-Feld roh holen und parsen
    raw_form = extract_value(text, "FähigkeitForm")
    parsed = _parse_form_field(raw_form or "")

    # Wenn Region gesetzt: wähle nur Einträge, deren Annotation die Region enthält
    if region and parsed:
        reg = region.lower()
        reg_non_vf = [name for name, anns in parsed if any(reg in a.lower() and 'vf' not in a.lower() for a in anns)]
        reg_vf = next((name for name, anns in parsed if any(reg in a.lower() and 'vf' in a.lower() for a in anns)), None)

        if reg_non_vf or reg_vf:
            return {
                "Faehigkeiten": reg_non_vf,
                "VersteckteFaehigkeit": reg_vf or base_vf
            }

    # Kein Region-Match (oder keine Region angegeben)
    if parsed:
        # Wenn kein Region-Filter angewendet wurde: gib alle form-abhängigen Fähigkeiten zurück,
        # wobei VF-Eintrag (falls vorhanden) separiert wird.
        non_vf = [name for name, anns in parsed if not any('vf' in a.lower() for a in anns)]
        vf_name = next((name for name, anns in parsed if any('vf' in a.lower() for a in anns)), None)
        if non_vf or vf_name:
            return {
                "Faehigkeiten": non_vf,
                "VersteckteFaehigkeit": vf_name or base_vf
            }

    # Fallback: Basis-Fähigkeiten zurückgeben
    fae = [f for f in [base_f1, base_f2] if f]
    return {
        "Faehigkeiten": fae,
        "VersteckteFaehigkeit": base_vf or ""
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
    entwicklungen = extract_entwicklungen(text, None)
    faehigkeiten = extract_faehigkeiten(text, pokemon_name)
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
    poki_name = "Lavados"
    entry = build_pokemon_entry(poki_name)
    if entry:
        save_to_cache(poki_name, entry)


if __name__ == "__main__":
    main()