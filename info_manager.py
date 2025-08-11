import json
from typing import Any, Dict, List, Optional

import attack_web_scraper
from information_storage import id_to_name_generator, fight_to_json_generator
import global_infos
from pokemon_web_scraper import get_pokemon_from_wiki

def get_type_of_pokemon(name: str) -> Optional[List[str]]:
    """
    Ruft die Typen eines Pokémons aus dem Cache ab.

    Args:
        name: Der Name des Pokémons.

    Returns:
        Eine Liste der Typen des Pokémons oder None.
    """
    pokemon_data = get_pokemon_in_cache(name)
    if pokemon_data:
        return pokemon_data.get("Typen")
    return None

def is_pokemon_in_cache(name: str) -> bool:
    """
    Überprüft, ob ein Pokémon im Cache vorhanden ist.
    
    Args:
        name: Der Name des Pokémons.
        
    Returns:
        True, wenn das Pokémon im Cache ist, sonst False.
    """
    try:
        with open(global_infos.POKEMON_CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        return name in cache_data
    except (FileNotFoundError, json.JSONDecodeError):
        # Datei nicht gefunden oder leer/fehlerhaft -> Pokémon ist nicht im Cache.
        return False

def get_pokemon_in_cache(name: str) -> Optional[Dict[str, Any]]:
    """
    Ruft die Daten eines Pokémons aus dem Cache ab.
    
    Diese Version wurde korrigiert, um direkt aus dem Cache zu lesen und nicht
    die Web-Scraping-Funktion aufzurufen.
    
    Args:
        name: Der Name des Pokémons.
        
    Returns:
        Ein Dictionary mit den Pokémon-Daten oder None, wenn es nicht gefunden wird.
    """
    ret = get_pokemon_from_wiki(name)
    return ret

def get_attack_in_cache(name: str):
    return attack_web_scraper.get_attack(name)

def get_attacks_of_pokemon(name: str) -> Optional[Dict[str, Any]]:
    ret = get_pokemon_in_cache(name).get("Attacken")
    return ret

def get_attacks_of_pokemon_as_list(pokemon_name):
    ret_list = list()
    for attack_type, attack_list in get_attacks_of_pokemon(pokemon_name).items():
        ret_list.append(attack_list)
    return ret_list

def get_attacken_of_pokemon_structured(pokemon_name: str, max_level: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Überarbeitete Funktion, die strukturierte Attacken-Daten für ein Pokémon
    der 8. Generation aus dem Cache-Dateien abruft.
    
    Die ursprüngliche Web-Scraping-Logik wurde durch die Verwendung der lokalen
    Cache-Dateien ersetzt.
    
    Args:
        pokemon_name: Der Name des Pokémons.
        max_level: Optional. Das maximale Level, bis zu dem Attacken gefiltert werden sollen.
        
    Returns:
        Eine Liste von Dictionaries, die jede erlernte Attacke detailliert beschreiben.
    """
    pokemon_attacks_by_type = get_attacks_of_pokemon(pokemon_name)
    if not pokemon_attacks_by_type:
        print(f"Keine Attacken-Daten für {pokemon_name} im Cache gefunden.")
        return []

    structured_attacks = []

    # Durchlaufe alle Attackenarten (LevelUp, TM, etc.)
    for attack_art, attacks_list in pokemon_attacks_by_type.items():
        for attack_entry in attacks_list:
            attack_name = attack_entry.get("Name")
            if not attack_name:
                continue

            # Spezielle Logik für LevelUp-Attacken
            if attack_art == "LevelUp":
                level_str = attack_entry.get("Level")
                try:
                    level_int = int(level_str)
                except (ValueError, TypeError):
                    level_int = 1 # Behandle 'Start' als Level 1

                # Filtern nach max_level, wenn angegeben
                if max_level is not None and level_int > max_level:
                    continue

            # Hole die Detaildaten der Attacke aus dem Attacken-Cache
            attack_details = get_attack_in_cache(attack_name)

            # Überspringen, wenn die Attacke nicht im Cache gefunden wird
            if not attack_details:
                print(f"Details für Attacke '{attack_name}' nicht im Cache gefunden.")
                continue

            # Erstelle das strukturierte Ergebnis-Dictionary
            result = {
                'Pokemon': pokemon_name,
                'Art': attack_art,
                'Name': attack_name,
                'Typ': attack_details.get('Typ'),
                'Kategorie': attack_details.get('Kategorie'),
                'Stärke': attack_details.get('Stärke'),
                'Genauigkeit': attack_details.get('Genauigkeit'),
                'AP': attack_details.get('AP')
            }

            # Füge das Level nur bei LevelUp-Attacken hinzu
            if attack_art == "LevelUp":
                result['Level'] = level_str
            else:
                result['Level'] = None # Oder ein anderer Standardwert

            structured_attacks.append(result)

    # Duplikate entfernen. Da der Cache bereits strukturiert ist,
    # ist die Duplikatlogik einfacher als im Original-Scraper.
    unique_attacks = {}
    for atk in structured_attacks:
        key = (atk['Name'], atk['Typ'], atk['Kategorie']) # Einfacher Schlüssel für Eindeutigkeit
        if key not in unique_attacks:
            unique_attacks[key] = atk

    return list(unique_attacks.values())


def get_name_from_id(id: str):
    return id_to_name_generator.get_german_name_by_id(id)


def get_trainer_team_from_trainer_name(trainer_name: str):
    """
    Sucht in allen Kämpfen nach Trainerteams anhand eines (Teil-)Namens.
    Gibt eine Liste aller passenden Kämpfe zurück.

    - trainer_name: Suchstring oder exakter Name
    - None oder leerer String -> leere Liste
    """
    if not trainer_name or not trainer_name.strip():
        return []  # Kein Name -> nichts gefunden

    trainer_name = trainer_name.strip().lower()
    matches = []

    for fight in fight_to_json_generator.get_all_fights():
        fight_name = fight.get("trainer_name", "")
        if fight_name and trainer_name in fight_name.lower():
            matches.append(fight)

    return matches
