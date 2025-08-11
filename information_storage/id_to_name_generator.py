import json
import re
from pathlib import Path

# Pfade
input_file = Path("information_storage/raw_id_to_name_data.txt")
output_file = Path("information_storage/id_to_name.json")

def parse_pokemon_data(file_path):
    id_to_name = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Nur Zeilen, die mit '|' beginnen und keine Header sind
            if not line.startswith("|") or line.startswith("!"):
                continue

            # Spalten aufteilen
            parts = [p.strip() for p in line.split("|") if p.strip()]

            if len(parts) < 3:
                continue

            # ID (erste Spalte)
            poke_id = parts[0]

            # Deutscher Name (3. Spalte)
            german_raw = parts[2]

            # [[Bisasam]] → Bisasam
            german_name = re.sub(r"\[\[(.*?)\]\]", r"\1", german_raw)

            id_to_name[poke_id] = german_name

    return id_to_name

def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_german_name_by_id(poke_id, json_path=output_file):
    poke_id = format_id_string(poke_id)
    data = load_json(json_path)
    return data.get(poke_id)

def format_id_string(id: str):
    return (4 - len(id)) * "0" + id

if __name__ == "__main__":
    mapping = parse_pokemon_data(input_file)
    save_json(mapping, output_file)
    print(f"Gespeichert in {output_file}")

    # Test
    print("Test:", get_german_name_by_id("0001"))
