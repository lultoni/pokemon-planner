import json
import re
import os
from pathlib import Path

import global_infos

# Speicherorte
RAW_FILE = Path("information_storage/raw_fight_data.txt")
OUTPUT_FILE = Path("information_storage/fight_data.json")

def parse_fights(raw_text):
    fights = []
    fight_blocks = re.findall(r"(\{\{Team/Kopf.*?\</div\>)", raw_text, re.S)

    current_location = None
    # Zeilenweise durchgehen, um Orte zu erkennen
    lines = raw_text.splitlines()
    block_index = 0

    while block_index < len(lines):
        line = lines[block_index]

        # Ortserkennung: === Trainer (XYZ) ===
        location_match = re.match(r"^===\s*Trainer\s*\(([^)]+)\)\s*===", line)
        if location_match:
            current_location = location_match.group(1).strip()

        # Kampfblock-Erkennung
        if line.startswith("{{Team/Kopf"):
            # Finde kompletten Block
            block_lines = []
            while block_index < len(lines):
                block_lines.append(lines[block_index])
                if "</div>" in lines[block_index]:
                    break
                block_index += 1
            block_text = "\n".join(block_lines)

            fights.extend(parse_fight_block(block_text, current_location))

        block_index += 1

    return fights


def parse_fight_block(block, location):
    local_fights = []

    header_match = re.search(r"\{\{Team/Kopf\|([^}]*)\}\}", block)
    header_content = header_match.group(1) if header_match else ""

    togglers = re.findall(r"toggler(\d+)=(.*?)\|", header_content + "|")
    togglerwahl_match = re.search(r"togglerwahl=([^|}]*)", header_content)
    togglerwahl = togglerwahl_match.group(1).strip() if togglerwahl_match else None

    team_lines = re.findall(r"\{\{Team/Zeile([^}]*)\}\}", block)

    if togglers:
        if togglerwahl and togglerwahl.lower() == "spielfortschritt":
            for idx, label in togglers:
                lines_for_group = [line for line in team_lines if f"togglershow{idx}=ja" in line]
                if lines_for_group:
                    fight = build_fight_from_lines(lines_for_group)
                    fight["location"] = location
                    local_fights.append(fight)
        else:
            starter_team_index = None
            for idx, starter_name in togglers:
                if starter_name.lower() == global_infos.starter_pokemon.lower():
                    starter_team_index = idx
                    break
            if starter_team_index:
                lines_for_group = [line for line in team_lines if f"togglershow{starter_team_index}=ja" in line]
                if lines_for_group:
                    fight = build_fight_from_lines(lines_for_group)
                    fight["location"] = location
                    local_fights.append(fight)
    else:
        if team_lines:
            fight = build_fight_from_lines(team_lines)
            fight["location"] = location
            local_fights.append(fight)

    return local_fights


def build_fight_from_lines(lines):
    fight_info = {}
    first_line = lines[0]
    fight_info["edition"] = get_field(first_line, "Edition")
    fight_info["trainer_class"] = get_field(first_line, "Trainerklasse")
    fight_info["trainer_name"] = get_field(first_line, "Trainername")
    fight_info["name"] = clean_wiki_links(get_field(first_line, "Name"))
    fight_info["reward_info"] = get_field(first_line, "GewinnZusatz")
    fight_info["hint"] = get_field(first_line, "Hinweis")
    fight_info["battle_type"] = get_field(first_line, "Kampfart")  # NEU

    pokemons = []
    for line in lines:
        for i in range(1, 7):
            if f"id{i}=" in line:
                poke = {
                    "ball": get_field(line, f"Ball{i}"),
                    "id": get_field(line, f"id{i}"),
                    "level": int(get_field(line, f"lvl{i}") or 0),
                    "gender": get_field(line, f"geschlecht{i}"),
                    "ability": get_field(line, f"fähigkeit{i}"),
                    "moves": [
                        get_field(line, f"atk{i}_{j}")
                        for j in range(1, 5)
                        if get_field(line, f"atk{i}_{j}")
                    ]
                }
                pokemons.append(poke)

    fight_info["team"] = pokemons
    return fight_info


def get_field(text, field):
    match = re.search(rf"\|{re.escape(field)}=([^|\n]*)", text)
    return match.group(1).strip() if match else None

def clean_wiki_links(value):
    if not value:
        return value
    return re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", value)

def get_all_fights(json_path: str = "information_storage/fight_data.json"):
    """
    Lädt alle Kämpfe aus der angegebenen JSON-Datei.
    Erwartet, dass die Datei eine Liste von Fight-Objekten enthält.

    :param json_path: Pfad zur JSON-Datei mit den Kämpfen
    :return: Liste aller Kämpfe (leere Liste, wenn Datei fehlt/fehlerhaft ist)
    """
    if not os.path.exists(json_path):
        print(f"[WARN] JSON-Datei nicht gefunden: {json_path}")
        return []

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("[WARN] JSON enthält keine Liste.")
            return []

        return data

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON-Parsing fehlgeschlagen: {e}")
        return []

def main():
    raw_text = RAW_FILE.read_text(encoding="utf-8")
    fights = parse_fights(raw_text)
    OUTPUT_FILE.write_text(json.dumps(fights, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Gespeichert: {OUTPUT_FILE} ({len(fights)} Kämpfe)")

if __name__ == "__main__":
    main()
