import json
import os

import pokemon_web_scraper


def get_all_pkm_names():
    # Build JSON path relative to this file (db_scraper_main.py)
    json_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "information_storage",
        "id_to_name.json"
    )

    # Normalize path (handles ../ properly)
    json_path = os.path.abspath(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        id_to_name = json.load(f)

    name_list = []

    for i in range(1, 152):
        if i < 10:
            i_string = f"000{i}"
        elif i < 100:
            i_string = f"00{i}"
        else:
            i_string = f"0{i}"

        name = id_to_name.get(i_string)
        if name:
            name_list.append(name)
        else:
            print(f"Warning: No entry for ID {i_string}")

    return name_list


if __name__ == "__main__":
    names = get_all_pkm_names()
    for name in names:
        pokemon_web_scraper.get_pokemon_from_wiki(name)
