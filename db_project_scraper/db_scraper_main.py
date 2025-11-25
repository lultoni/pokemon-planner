import json
import os
import pokemon_web_scraper
import attack_web_scraper


def get_all_pkm_names():
    # Build JSON path relative to this file (db_scraper_main.py)
    json_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "information_storage",
        "id_to_name.json"
    )
    json_path = os.path.abspath(json_path)

    with open(json_path, "r", encoding="utf-8") as f:
        id_to_name = json.load(f)

    name_list = []

    for i in range(1, 152):  # Gen-1: 001 - 151
        i_string = f"{i:04d}"  # Formats to 0001, 0002, ... 0151

        name = id_to_name.get(i_string)
        if name:
            name_list.append(name)
        else:
            print(f"⚠️  Warning: No Pokémon entry for ID {i_string}")

    return name_list


def load_attack_cache():
    attack_cache_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "information_storage",
        "attack_cache.json"
    )
    attack_cache_path = os.path.abspath(attack_cache_path)

    if not os.path.exists(attack_cache_path):
        return {}, attack_cache_path

    with open(attack_cache_path, "r", encoding="utf-8") as f:
        try:
            cache = json.load(f)
            if isinstance(cache, list):
                # If needed, convert legacy list cache
                cache = {item["Name"]: item for item in cache}
        except Exception:
            cache = {}

    return cache, attack_cache_path


if __name__ == "__main__":
    print("🔵 Loading Gen-1 Pokémon list ...")
    pokemon_names = get_all_pkm_names()

    print("🔵 Loading Attack cache ...")
    attack_cache, attack_cache_path = load_attack_cache()

    # Sammle Attackennamen, die nach dem Pokémon-Scrape auftauchen
    missing_attacks = set()

    print("\n===== 🔷 SCRAPING POKÉMON =====\n")

    for name in pokemon_names:
        print(f"➡️  Scraping Pokémon: {name}")
        data = pokemon_web_scraper.get_pokemon_from_wiki(name)

        if not data:
            print(f"❌ No data returned for: {name}")
            continue

        # Aus dem zurückgegebenen Pokémon-Objekt Attackennamen extrahieren
        attacks = data.get("Attacken") or {}
        for category, moves in attacks.items():
            for move in moves:
                move_name = move.get("Name") if isinstance(move, dict) else None
                if move_name:
                    if move_name not in attack_cache:
                        missing_attacks.add(move_name)

    print("\n===== 🟡 SCRAPING ATTACKS =====\n")

    if not missing_attacks:
        print("✔️  No missing attacks – all already cached.")
    else:
        print(f"📝 Need to scrape {len(missing_attacks)} new attacks\n")

    for atk_name in sorted(missing_attacks):
        print(f"➡️  Scraping attack: {atk_name}")
        try:
            data = attack_web_scraper.get_attack(atk_name)
        except Exception as e:
            print(f"   ❗ Error scraping '{atk_name}': {e}")

    print("\n===== 🎉 DONE =====")
    print(f"Scraped all Gen-1 Pokémon and updated attack cache at:")
    print(f"   {attack_cache_path}")
