import json
from typing import List, Dict, Any, Optional

from global_infos import POKEMON_CACHE_FILE_PATH

def get_type_of_pokemon(name: str) -> Optional[List[str]]:
    """
    Ruft die Typen eines Pokémon ab.

    Sucht zuerst im lokalen Cache. Wenn das Pokémon nicht im Cache gefunden wird,
    sollte idealerweise ein Web-Scraper aufgerufen werden, um die Daten zu holen.
    
    Args:
        name: Der Name des Pokémon (z.B. "Zigzachs").

    Returns:
        Eine Liste der Typen (z.B. ["Unlicht", "Normal"]) oder None, 
        wenn das Pokémon nicht gefunden wurde.
    """
    pokemon_data = get_pokemon_in_cache(name)

    if pokemon_data:
        return pokemon_data.get("Typen") # .get() ist sicherer als direkter Zugriff

    from pokemon_web_scraper import get_pokemon_from_wiki
    pokemon_data = get_pokemon_from_wiki(name)
    if pokemon_data:
        return pokemon_data.get("Typen")

    return None

def is_pokemon_in_cache(name: str) -> bool:
    """
    Überprüft, ob ein Pokémon bereits im JSON-Cache vorhanden ist.

    Args:
        name: Der Name des Pokémon.

    Returns:
        True, wenn das Pokémon im Cache ist, ansonsten False.
    """
    try:
        with open(POKEMON_CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        return name in cache_data
    except (FileNotFoundError, json.JSONDecodeError):
        # Datei nicht gefunden oder leer/fehlerhaft -> Pokémon ist nicht im Cache.
        return False

def get_pokemon_in_cache(name: str) -> Optional[Dict[str, Any]]:
    """
    Holt den vollständigen Datensatz eines Pokémon aus dem JSON-Cache.

    Args:
        name: Der Name des Pokémon.

    Returns:
        Ein Dictionary mit den Daten des Pokémon oder None, wenn es nicht gefunden wurde.
    """
    if not is_pokemon_in_cache(name):
        return None

    try:
        with open(POKEMON_CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        # .get(name) gibt None zurück, falls der Schlüssel doch nicht existiert.
        return cache_data.get(name)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# todo add attack cache functionality

# todo add trainer battle cache functionality