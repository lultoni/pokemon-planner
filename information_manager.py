import json
from typing import List, Dict, Any, Optional

import attack_web_scraper
from global_infos import POKEMON_CACHE_FILE_PATH
from pokemon_web_scraper import get_pokemon_from_wiki

def get_type_of_pokemon(name: str) -> Optional[List[str]]:
    pokemon_data = get_pokemon_in_cache(name)

    if pokemon_data:
        return pokemon_data.get("Typen") # .get() ist sicherer als direkter Zugriff

    return None

def is_pokemon_in_cache(name: str) -> bool:
    try:
        with open(POKEMON_CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        return name in cache_data
    except (FileNotFoundError, json.JSONDecodeError):
        # Datei nicht gefunden oder leer/fehlerhaft -> Pokémon ist nicht im Cache.
        return False

def get_pokemon_in_cache(name: str) -> Optional[Dict[str, Any]]:
    if not is_pokemon_in_cache(name):
        return None

    return get_pokemon_from_wiki(name)

def get_attack_in_cache(name: str):
    return attack_web_scraper.get_attack(name)

def get_attacks_of_pokemon(name: str):
    return get_pokemon_in_cache(name).get("Attacken")
# todo add trainer battle cache functionality