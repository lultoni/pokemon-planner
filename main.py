import global_infos
import information_manager
import type_effectiveness
from tqdm import tqdm # Importiere die tqdm-Bibliothek

def main():
    print("Analyse Start")

    opponent_data = information_manager.get_trainer_team_from_trainer_name(global_infos.opponent_trainer_name)[0]
    opponent_team = opponent_data["team"]
    raw_damage_table_player_to_opponent = []

    # Hier werden alle Iterationen gezählt, um die Fortschrittsanzeige zu initialisieren
    total_iterations = len(global_infos.owned_pokemon_list) * len(opponent_team)

    # Verwende tqdm, um eine Fortschrittsanzeige zu erstellen
    # Die Fortschrittsanzeige wird für jeden Vergleich von 1vs1 Pokémon geupdated
    with tqdm(total=total_iterations, desc="Gesamtanalyse") as pbar:
        for own_pkm_name in global_infos.owned_pokemon_list:
            own_pkm = information_manager.get_pokemon_in_cache(own_pkm_name)

            # Attacken einmalig außerhalb der inneren Schleife laden
            all_own_moves = information_manager.get_attacks_of_pokemon_as_list(own_pkm_name)

            for opp_pkm_battle_data in opponent_team:
                opp_pkm = information_manager.get_pokemon_in_cache(information_manager.get_name_from_id(opp_pkm_battle_data["id"]))

                best_own_move = ["error_name", -1]

                for attack_list in all_own_moves:
                    for own_move_data in attack_list:
                        own_move_name = own_move_data["Name"]
                        own_move = information_manager.get_attack_in_cache(own_move_name)

                        # Vereinfachte Logik für Kategorie, Stärke und Genauigkeit
                        is_special_attack = own_move["Kategorie"] == "Speziell"
                        attack_stat_key = "SpAngriff" if is_special_attack else "Angriff"
                        defense_stat_key = "SpVerteidigung" if is_special_attack else "Verteidigung"
                        attack_stat = own_pkm["Statuswerte"][attack_stat_key]
                        defense_stat = opp_pkm["Statuswerte"][defense_stat_key]

                        power_of_move = 1
                        if own_move["Stärke"] == "K.O.":
                            power_of_move = 255
                        elif own_move["Stärke"] and own_move["Stärke"].isdigit():
                            power_of_move = int(own_move["Stärke"])
                        elif own_move_name == "Schleuder":
                            power_of_move = 30
                        elif own_move_name in ["Strauchler", "Rammboss"]:
                            power_of_move = 60
                        elif own_move_name == "Dreschflegel":
                            power_of_move = 40
                        else:
                            power_of_move = 10 # Standardwert für unbestimmte Stärken

                        stab_bonus = 1.5 if own_move["Typ"] in own_pkm["Typen"] else 1
                        move_effectiveness = type_effectiveness.get_effectiveness(own_move["Typ"], opp_pkm["Typen"])

                        raw_damage = power_of_move * (attack_stat / max(defense_stat, 1)) * move_effectiveness * stab_bonus

                        accuracy = 1
                        if own_move["Genauigkeit"] and own_move["Genauigkeit"].isdigit():
                            accuracy = int(own_move["Genauigkeit"]) / 100
                        elif own_move_name == "Eiseskälte":
                            accuracy = 0.25
                        else:
                            accuracy = 0.5 # Standardwert für unbestimmte Genauigkeit

                        expected_damage = raw_damage * accuracy

                        if expected_damage > best_own_move[1]:
                            best_own_move = [own_move_name, expected_damage]

                raw_damage_table_player_to_opponent.append([own_pkm_name, information_manager.get_name_from_id(opp_pkm_battle_data["id"]), best_own_move])
                pbar.update(1) # Die Fortschrittsanzeige aktualisieren

    for entry in raw_damage_table_player_to_opponent:
        print(entry)
    print("Analyse Ende")

if __name__ == "__main__":
    main()