import global_infos
import information_manager
import type_effectiveness


def main():
    print("Analyse Start")

    opponent_data = information_manager.get_trainer_team_from_trainer_name(global_infos.opponent_trainer_name)[0]
    opponent_team = opponent_data["team"]
    raw_damage_table_player_to_opponent = []
    raw_damage_table_opponent_to_player = []

    for own_pkm_name in global_infos.owned_pokemon_list:
        own_pkm = information_manager.get_pokemon_in_cache(own_pkm_name)
        #print(own_pkm["Attacken"])
        for opp_pkm_battle_data in opponent_team:
            opp_pkm = information_manager.get_pokemon_in_cache(information_manager.get_name_from_id(opp_pkm_battle_data["id"]))
            best_own_move = ["error_name", -1]
            for attack_list in information_manager.get_attacks_of_pokemon_as_list(own_pkm_name):
                for own_move_data in attack_list:
                    own_move_name = own_move_data["Name"]
                    own_move = information_manager.get_attack_in_cache(own_move_name)
                    if own_move["Kategorie"] == "Physisch":
                        _temp_val = ""
                    else:
                        _temp_val = "Sp"
                    attack_stat = own_pkm["Statuswerte"][f"{_temp_val}Angriff"]
                    defense_stat = opp_pkm["Statuswerte"][f"{_temp_val}Verteidigung"]
                    if not own_move["Stärke"]:
                        _temp_val = 0
                    elif own_move["Stärke"] == "K.O.":
                        _temp_val = 255 # todo decide how you want to handle this (could also go with 999 i suppose)
                    elif own_move["Stärke"] == "variiert" or own_move["Stärke"] == "—":
                        if own_move_name == "Schleuder":
                            _temp_val = 30
                        elif own_move_name == "Strauchler" or own_move_name == "Rammboss":
                            _temp_val = 60
                        elif own_move_name == "Dreschflegel":
                            _temp_val = 40
                        else:
                            print(own_move_name)
                            _temp_val = 10 # todo decide how you want to handle this
                    else:
                        _temp_val = int(own_move["Stärke"])
                    power_of_move = max(_temp_val, 10)
                    _temp_val = own_move["Typ"] in own_pkm["Typen"]
                    if _temp_val:
                        stab_bonus = 1.5
                    else:
                        stab_bonus = 1
                    move_effectiveness = type_effectiveness.get_effectiveness(own_move["Typ"], opp_pkm["Typen"])

                    raw_damage = power_of_move * (attack_stat / max(defense_stat, 1)) * move_effectiveness * stab_bonus
                    if not own_move["Genauigkeit"]:
                        _temp_val = 1
                    elif own_move["Genauigkeit"] == "variiert" or "—":
                        if own_move_name == "Eiseskälte":
                            _temp_val = 0.25
                        else:
                            print(own_move_name)
                            _temp_val = 0.5 # todo decide how you want to handle this
                    else:
                        _temp_val = int(own_move["Genauigkeit"])/100
                    expected_damage = raw_damage * _temp_val
                    if expected_damage > best_own_move[1]:
                        best_own_move = [own_move_name, expected_damage]
            raw_damage_table_player_to_opponent.append([own_pkm_name, information_manager.get_name_from_id(opp_pkm_battle_data["id"]), best_own_move])

    print(raw_damage_table_player_to_opponent)

    print("Analyse Ende")


if __name__ == "__main__":
    main()