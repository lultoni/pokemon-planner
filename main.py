import global_infos
import information_manager
import type_effectiveness
from tqdm import tqdm # Importiere die tqdm-Bibliothek
import math

def _parse_power(own_move_name, own_move):
    """
    Extrahiere eine numerische Power aus own_move (falls vorhanden),
    sonst weiche auf bekannte Sonderfälle oder Standardwert aus.
    """
    if own_move is None:
        return 10
    Stärke = own_move.get("Stärke")
    if Stärke == "K.O.":
        return 255
    if Stärke and isinstance(Stärke, str) and Stärke.isdigit():
        return int(Stärke)
    # Sonderfälle (deine bisherigen Zuordnungen)
    if own_move_name == "Schleuder":
        return 30
    if own_move_name in ["Strauchler", "Rammboss"]:
        return 60
    if own_move_name == "Dreschflegel":
        return 40
    # Default für unbekannte/Status-Moves
    return 10

def _infer_category_from_base(atk_stats):
    """
    Kleine Heuristik: wenn Basis-Angriff größer als Basis-SpAngriff -> physical,
    sonst special. atk_stats ist dict mit "Angriff" und "SpAngriff".
    """
    atk = atk_stats.get("Angriff", 0)
    spatk = atk_stats.get("SpAngriff", 0)
    return "physisch" if atk >= spatk else "speziell"

def determine_move_category(move_meta, move_in_cache, attacker_pkm):
    """
    Bestimme die Kategorie eines Moves (pro Move!).
    Priorität:
      1) move_meta (die Liste, die du von get_attacks_of_pokemon_as_list bekommst), falls dort 'Kategorie' existiert
      2) move_in_cache (vollständige Move-Daten) falls dort 'Kategorie' existiert
      3) Fallback: schätze anhand der Base-Stats des Angreifers (wie vorher)
    Rückgabe: string 'physisch' oder 'speziell' (dein Code nutzt diese Strings)
    """
    # 1) move_meta hat manchmal schon Kategorie-Info (z. B. "Schaufler" Eintrag)
    if move_meta and isinstance(move_meta, dict):
        cat = move_meta.get("Kategorie")
        if cat:
            return cat

    # 2) move_in_cache ist detaillierter (falls vorhanden)
    if move_in_cache and isinstance(move_in_cache, dict):
        cat = move_in_cache.get("Kategorie")
        if cat:
            return cat

    # 3) Fallback auf Basiswerte des Angreifers (wie bisher)
    atk = attacker_pkm["Statuswerte"].get("Angriff", 0)
    spatk = attacker_pkm["Statuswerte"].get("SpAngriff", 0)
    return "physisch" if atk >= spatk else "speziell"

def compute_best_raw_for_pair(attacker_pkm, attacker_name, defender_pkm, attacker_moves_list):
    """
    Berechnet für einen Angreifer (attacker_pkm) gegen einen Defender (defender_pkm)
    den besten raw-Wert über alle Moves des Angreifers (ohne Accuracy/STAB).
    attacker_moves_list muss die gleiche Struktur haben wie in deinem Code:
      eine Liste von attack-listen (wie get_attacks_of_pokemon_as_list liefert).
    """
    best_raw = 0.0
    # Wenn keine Moves bekannt -> fallback: keine Moves => raw 0 (oder kleiner Default)
    if not attacker_moves_list:
        return best_raw

    for attack_list in attacker_moves_list:
        for move_meta in attack_list:
            if not move_meta:
                continue
            move_name = move_meta.get("Name", "")
            move_in_cache = information_manager.get_attack_in_cache(move_name)

            # Power bestimmen (falls move_in_cache vorhanden, nutze _parse_power, sonst Default)
            if move_in_cache:
                power = _parse_power(move_name, move_in_cache)
                move_type = move_in_cache.get("Typ")
            else:
                power = 10
                move_type = None

            # WICHTIG: Kategorie pro MOVE bestimmen (nicht per Pokémon-Stat)
            category = determine_move_category(move_meta, move_in_cache, attacker_pkm)

            # Stats wählen basierend auf der tatsächlich bestimmten Kategorie
            if category.lower().startswith("s"):  # 'Speziell' oder ähnlich
                attack_stat = attacker_pkm["Statuswerte"].get("SpAngriff", 0.0)
                defense_stat = defender_pkm["Statuswerte"].get("SpVerteidigung", 1.0)
            else:
                attack_stat = attacker_pkm["Statuswerte"].get("Angriff", 0.0)
                defense_stat = defender_pkm["Statuswerte"].get("Verteidigung", 1.0)
            defense_stat = max(defense_stat, 1.0)

            # Type effectiveness (falls move_type unbekannt -> eff = 1.0)
            if move_type:
                try:
                    eff = type_effectiveness.get_effectiveness(move_type, defender_pkm["Typen"])
                except Exception:
                    eff = 1.0
            else:
                eff = 1.0

            raw = power * (attack_stat / defense_stat) * eff
            if raw > best_raw:
                best_raw = raw
    return best_raw

def main():
    print("Analyse Start")

    opponent_data = information_manager.get_trainer_team_from_trainer_name(global_infos.opponent_trainer_name)[0]
    opponent_team = opponent_data["team"]
    print(" ~ Fetched Opponent Data")

    owned_list = global_infos.owned_pokemon_list
    print(" ~ Fetched Own Pokemon")

    # Wir berechnen beide Richtungen -> Fortschrittsbar entsprechend anpassen
    total_iterations = len(owned_list) * len(opponent_team) * 2

    # Dictionaries: nested mapping attacker_name -> defender_name -> raw_value
    raw_player_to_opponent = {}
    raw_opponent_to_player = {}
    print(" ~ Initialized Mapping Dictionaries")

    # Preload move-lists for all Pokémon (schneller repeated access)
    moves_cache = {}
    for own_pkm_name in owned_list:
        moves_cache[own_pkm_name] = information_manager.get_attacks_of_pokemon_as_list(own_pkm_name)
    print(" ~ Stored All Own Moves")
    opp_moves_cache = {}
    for opp_fight_data_pkm in opponent_team:
        opp_name = information_manager.get_name_from_id(opp_fight_data_pkm["id"])
        pkm_attack_list = [[]]
        for move_name in opp_fight_data_pkm["moves"]:
            pkm_attack_list[0].append(information_manager.get_attack_in_cache(move_name))
        opp_moves_cache[opp_name] = pkm_attack_list
    print(" ~ Stored All Opponent Moves")

    with tqdm(total=total_iterations, desc="Gesamtanalyse") as pbar:
        # Spieler -> Gegner
        for own_pkm_name in owned_list:
            own_pkm = information_manager.get_pokemon_in_cache(own_pkm_name)
            attacker_moves_list = moves_cache.get(own_pkm_name, [])
            raw_player_to_opponent.setdefault(own_pkm_name, {})
            for opp_fight_data_pkm in opponent_team:
                opp_name = information_manager.get_name_from_id(opp_fight_data_pkm["id"])
                opp_pkm = information_manager.get_pokemon_in_cache(opp_name)

                best_raw = compute_best_raw_for_pair(own_pkm, own_pkm_name, opp_pkm, attacker_moves_list)
                raw_player_to_opponent[own_pkm_name][opp_name] = best_raw

                pbar.update(1)

        # Gegner -> Spieler
        for opp_fight_data_pkm in opponent_team:
            opp_name = information_manager.get_name_from_id(opp_fight_data_pkm["id"])
            opp_pkm = information_manager.get_pokemon_in_cache(opp_name)
            attacker_moves_list = opp_moves_cache.get(opp_name, [])
            raw_opponent_to_player.setdefault(opp_name, {})
            for own_pkm_name in owned_list:
                own_pkm = information_manager.get_pokemon_in_cache(own_pkm_name)

                best_raw = compute_best_raw_for_pair(opp_pkm, opp_name, own_pkm, attacker_moves_list)
                raw_opponent_to_player[opp_name][own_pkm_name] = best_raw

                pbar.update(1)

    # -> Normalisierung (Min-Max über alle raw Werte beider Tabellen)
    all_raw_values = []
    for a in raw_player_to_opponent.values():
        all_raw_values.extend(a.values())
    for a in raw_opponent_to_player.values():
        all_raw_values.extend(a.values())

    # Falls keine Werte vorhanden (leere Pools) handle edge-case
    if not all_raw_values:
        print("Keine raw-Werte gefunden. Abbruch.")
        return

    vmin = min(all_raw_values)
    vmax = max(all_raw_values)

    damage_player_to_opponent = {}
    damage_opponent_to_player = {}

    if math.isclose(vmin, vmax):
        # Edge-Case: alle Werte identisch => setze 0.5
        for atk, d in raw_player_to_opponent.items():
            damage_player_to_opponent[atk] = {defn: 0.5 for defn in d}
        for atk, d in raw_opponent_to_player.items():
            damage_opponent_to_player[atk] = {defn: 0.5 for defn in d}
    else:
        span = vmax - vmin
        for atk, d in raw_player_to_opponent.items():
            damage_player_to_opponent[atk] = {defn: (val - vmin) / span for defn, val in d.items()}
        for atk, d in raw_opponent_to_player.items():
            damage_opponent_to_player[atk] = {defn: (val - vmin) / span for defn, val in d.items()}

    # Ausgabe: (optional) print normalized damage scores in ähnlichem Format wie vorher
    print("=== Normalized damage player -> opponent (0..1) ===")
    for own_name, mapping in damage_player_to_opponent.items():
        for opp_name, score in mapping.items():
            print([own_name, opp_name, round(score, 4)])

    print("=== Normalized damage opponent -> player (0..1) ===")
    for opp_name, mapping in damage_opponent_to_player.items():
        for own_name, score in mapping.items():
            print([opp_name, own_name, round(score, 4)])

    print("Analyse Ende")

if __name__ == "__main__":
    main()
