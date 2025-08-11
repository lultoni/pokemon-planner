import global_infos
import info_manager
import type_effectiveness
from tqdm import tqdm # Importiere die tqdm-Bibliothek
import math

# Status moves zählen wir, wenn die Move-Kategorie "Status" ist (so vorhanden)
MAX_TOP_PER_OPP = 3

# Hinweis: falls es unterschiedliche Schreibweisen in deinem Cache gibt (z. B. 'Giga-Lichtblick' vs 'Giga Lichtblick'),
# kannst du noch zusätzliche Varianten hinzufügen oder beim Vergleich non-alphanumerische Zeichen entfernen.


def _parse_power(own_move_name, own_move):
    """
    Extrahiere eine numerische Power aus own_move (falls vorhanden),
    sonst weiche auf bekannte Sonderfälle oder Standardwert aus.
    """
    if own_move is None:
        return global_infos.default_strength_move

    if own_move.get("Kategorie") == "Status":
        return 0 # todo how do you wanna handle status moves

    strength = own_move.get("Stärke")
    if strength == "K.O.":
        return 255
    if strength and isinstance(strength, str) and strength.isdigit():
        return int(strength)
    # Sonderfälle (deine bisherigen Zuordnungen)
    if own_move_name == "Schleuder":
        return 30
    if own_move_name in ["Strauchler", "Rammboss"]:
        return 60
    if own_move_name == "Dreschflegel":
        return 40

    # Default für unbekannte
    return global_infos.default_strength_move

def _parse_accuracy(move_name: str, move_data: dict) -> float:
    """
    Ermittelt die Genauigkeit einer Attacke als Float-Wert (z.B. 95 -> 0.95).
    Behandelt spezielle Fälle und Standardwerte.
    """
    # Wenn keine Move-Daten vorhanden sind, nehmen wir einen sicheren Standardwert an.
    if not move_data:
        return 0.7  # Allgemeiner Standardwert

    accuracy_str = move_data.get("Genauigkeit")

    if accuracy_str and accuracy_str.isdigit():
        return int(accuracy_str) / 100.0

    # Spezielle Fälle aus deinem alten Code
    if move_name == "Eiseskälte":
        return 0.3 # Genauigkeit für OHKO-Moves ist 30%

    # Wenn die Genauigkeit nicht numerisch oder nicht vorhanden ist (z.B. "---"),
    # bedeutet das oft, dass die Attacke immer trifft (z.B. Aero-Ass).
    # Wir nehmen hier 1.0 (100%) an.
    if not accuracy_str or accuracy_str == '---':
        return 1.0

    # Fallback für andere nicht-numerische Werte
    return 0.85 # Sicherer Standardwert, wenn etwas Unerwartetes passiert

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

def compute_best_damage_for_pair(attacker_pkm, attacker_name, defender_pkm, attacker_moves_list):
    """
    Berechnet für einen Angreifer gegen einen Defender den besten *erwarteten Schaden*
    über alle Moves, unter Einbeziehung von STAB und Genauigkeit.
    Gibt am Ende den Rechenweg für den besten gefundenen Move aus.
    """
    # GEÄNDERT: Wir optimieren jetzt für den erwarteten Schaden
    best_expected_damage = 0.0
    best_calculation_details = {}

    if not attacker_moves_list:
        # GEÄNDERT: Passender Rückgabewert für den Fehlerfall
        return 0.0, None

    # NEU: Typen des Angreifers für STAB-Berechnung einmalig holen
    attacker_types = attacker_pkm.get("Typen", [])

    for attack_list in attacker_moves_list:
        for move_meta in attack_list:
            if not move_meta:
                continue
            move_name = move_meta.get("Name", "")
            move_in_cache = info_manager.get_attack_in_cache(move_name)

            if move_in_cache:
                power = _parse_power(move_name, move_in_cache)
                move_type = move_in_cache.get("Typ")
            else:
                print(f"Move not in Cache whilst computing damage - Name: {move_name}")
                power = global_infos.default_strength_move
                move_type = None

            # NEU: Genauigkeit der Attacke bestimmen
            accuracy = _parse_accuracy(move_name, move_in_cache)

            # NEU: STAB-Bonus bestimmen
            stab_bonus = 1.5 if move_type in attacker_types else 1.0

            category = determine_move_category(move_meta, move_in_cache, attacker_pkm)

            if category.lower().startswith("s"):
                attack_stat = attacker_pkm["Statuswerte"].get("SpAngriff", 0.0)
                defense_stat = defender_pkm["Statuswerte"].get("SpVerteidigung", 1.0)
            else:
                attack_stat = attacker_pkm["Statuswerte"].get("Angriff", 0.0)
                defense_stat = defender_pkm["Statuswerte"].get("Verteidigung", 1.0)
            defense_stat = max(defense_stat, 1.0)

            if move_type:
                try:
                    eff = type_effectiveness.get_effectiveness(move_type, defender_pkm["Typen"])
                except Exception:
                    eff = 1.0
            else:
                eff = 1.0

            # GEÄNDERT: Formel erweitert um STAB
            raw_damage = power * (attack_stat / defense_stat) * eff * stab_bonus
            # NEU: Berechnung des erwarteten Schadens
            expected_damage = raw_damage * accuracy

            # GEÄNDERT: Vergleich basiert jetzt auf expected_damage
            if expected_damage > best_expected_damage:
                best_expected_damage = expected_damage
                best_calculation_details = {
                    "move_name": move_name,
                    "power": power,
                    "attack_stat": attack_stat,
                    "defense_stat": defense_stat,
                    "effectiveness": eff,
                    "stab_bonus": stab_bonus, # NEU im Dictionary
                    "accuracy": accuracy,     # NEU im Dictionary
                    "raw_damage": raw_damage  # NEU zur Anzeige
                }

    if best_calculation_details:
        defender_name = info_manager.get_name_from_id(defender_pkm.get("ID"))
        details = best_calculation_details

        # GEÄNDERT: Ausgabe erweitert
        print("\n--- Bester erwarteter Schaden ---")
        print(f"Angreifer: {attacker_name}")
        print(f"Verteidiger: {defender_name}")
        print(f"Beste Attacke: {details['move_name']}")
        print(f"Roher Schaden (vor Genauigkeit): {details['raw_damage']:.2f}")
        print("-" * 20)
        print(f"Formel: power * (att/def) * eff * STAB * accuracy")
        print(f"Werte: {details['power']} * ({details['attack_stat']:.0f}/{details['defense_stat']:.0f}) * {details['effectiveness']} * {details['stab_bonus']} * {details['accuracy']}")
        print(f"Erwarteter Schaden: {best_expected_damage:.2f}")
        print("--------------------------------\n")
    else:
        # Sinnvollere Ausgabe, wenn keine Attacken gefunden wurden
        print(f"Keine effektiven Attacken für {attacker_name} gegen {info_manager.get_name_from_id(defender_pkm.get('ID'))} gefunden.")

    # GEÄNDERT: Gib den besten Schaden und den Namen der Attacke zurück
    return best_expected_damage, best_calculation_details.get('move_name')

def compute_utility_score_for_attacker(attacker_name, attacker_moves_list):
    """
    Einfache Heuristik (0..1):
    - hat Recovery (Move-Name ist in HEALING_MOVES) -> +0.25
    - Anzahl Status-Moves (Kategorie == 'Status') -> +0.12 pro Move (max. +0.5)
    Wichtig: Es wird **nur** auf Move-Namen geprüft (keine Effekt-/Beschreibungssuche).
    """
    score = 0.0
    status_count = 0
    has_recovery = False

    for attack_list in attacker_moves_list:
        for move_meta in attack_list:
            if not move_meta:
                continue
            move_name = (move_meta.get("Name") or "").strip()
            move_name_norm = move_name.lower()

            # Recovery-Erkennung ausschliesslich über Move-Name
            if move_name_norm in global_infos.HEALING_MOVES:
                has_recovery = True

            # Status detection: prefer move_cache Kategorie, fallback auf move_meta
            move_cache = info_manager.get_attack_in_cache(move_name) if move_name else None
            cat = None
            if move_cache and isinstance(move_cache, dict):
                cat = move_cache.get("Kategorie")
            if not cat:
                cat = move_meta.get("Kategorie")
            if cat and str(cat).lower().startswith("s"):  # 'Status'...
                status_count += 1

    if has_recovery:
        score += 0.25
    score += min(0.5, status_count * 0.12)  # cap bei 0.5
    return min(1.0, score)

def get_farbigen_wert_string(wert: float) -> str:
    """
    Nimmt einen Float-Wert zwischen 0.0 und 1.0 und gibt ihn als
    farbigen String für die Konsole zurück.
    Der Farbverlauf geht von Rot (0.0) über Grau (0.5) zu Grün (1.0).

    Args:
        wert: Eine Fließkommazahl zwischen 0.0 und 1.0.

    Returns:
        Einen String, der den Wert mit ANSI-Farbcodes enthält.
        Gibt den Wert ohne Farbe zurück, wenn er außerhalb des Bereichs liegt.
    """
    # --- Input-Validierung ---
    # Stellt sicher, dass der Wert im gültigen Bereich liegt.
    if not (0.0 <= wert <= 1.0):
        return str(wert)

    # --- Farb-Berechnung (Lineare Interpolation) ---
    # Wir definieren einen zweistufigen Gradienten:
    # 1. Von Rot (255, 0, 0) zu Grau (128, 128, 128) für Werte von 0.0 bis 0.5
    # 2. Von Grau (128, 128, 128) zu Grün (0, 255, 0) für Werte von 0.5 bis 1.0

    if wert <= 0.5:
        # Skaliere den Wert auf den Bereich 0 bis 1 für die erste Hälfte
        t = wert * 2
        # Interpoliere von Rot (255, 0, 0) zu Grau (128, 128, 128)
        r = int(255 + (128 - 255) * t)
        g = int(0 + (128 - 0) * t)
        b = int(0 + (128 - 0) * t)
    else: # wert > 0.5
        # Skaliere den Wert auf den Bereich 0 bis 1 für die zweite Hälfte
        t = (wert - 0.5) * 2
        # Interpoliere von Grau (128, 128, 128) zu Grün (0, 255, 0)
        r = int(128 + (0 - 128) * t)
        g = int(128 + (255 - 128) * t)
        b = int(128 + (0 - 128) * t)

    # --- String-Formatierung mit ANSI-Farbcodes ---
    # \033[38;2;r;g;bm -> Setzt die Vordergrundfarbe (Text) auf den RGB-Wert
    # \033[0m          -> Setzt alle Formatierungen zurück (wichtig!)

    # Formatieren des Wertes auf z.B. 2 Nachkommastellen für eine saubere Ausgabe
    wert_str = f"{wert:.2f}"

    return f"\033[38;2;{r};{g};{b}m{wert_str}\033[0m"

def calculate_survival_score(own_pkm_data: dict, opponent_pkm_data: dict, incoming_damage: float, outgoing_damage: float, vmin: float, vmax: float) -> float:
    """
    Berechnet einen Survival-Score, der die Initiative und OHKO-Potenzial berücksichtigt.

    Args:
        own_pkm_data: Das Daten-Dictionary des eigenen Pokémon.
        opponent_pkm_data: Das Daten-Dictionary des gegnerischen Pokémon.
        incoming_damage: Der beste erwartete Schaden, den der Gegner uns zufügt.
        outgoing_damage: Der beste erwartete Schaden, den wir dem Gegner zufügen.
        vmin, vmax: Normalisierungswerte für die Schadensberechnung.

    Returns:
        Einen Survival-Score zwischen 0.0 und 1.0.
    """
    # 1. Benötigte Statuswerte extrahieren
    my_hp = own_pkm_data.get("Statuswerte", {}).get("KP", 1.0)
    my_speed = own_pkm_data.get("Statuswerte", {}).get("Initiative", 0.0)

    opponent_hp = opponent_pkm_data.get("Statuswerte", {}).get("KP", 1.0)
    opponent_speed = opponent_pkm_data.get("Statuswerte", {}).get("Initiative", 0.0)

    # Sicherstellen, dass HP nicht 0 ist, um Division durch Null zu vermeiden
    my_hp = max(my_hp, 1.0)
    opponent_hp = max(opponent_hp, 1.0)

    # 2. Grundlegende Berechnungen vorbereiten

    # Deine ursprüngliche Formel für den erlittenen Schaden in %
    # (hier wird der normalisierte Schaden durch die KP geteilt)
    scaled_incoming_damage = ((vmax - vmin) * incoming_damage + vmin)
    damage_percentage_if_hit = min(scaled_incoming_damage / my_hp, 1.0)

    # Der Survival-Score, WENN du getroffen wirst
    survival_if_hit = 1.0 - damage_percentage_if_hit

    # Prüfen, ob du den Gegner mit einem Schlag besiegen kannst
    can_i_ohko_opponent = outgoing_damage >= opponent_hp

    # 3. Die drei Szenarien basierend auf der Initiative auswerten

    # Szenario 1: Du bist schneller
    if my_speed > opponent_speed:
        if can_i_ohko_opponent:
            # Du besiegst den Gegner, bevor er angreifen kann.
            return 1.0  # Perfektes Überleben
        else:
            # Du schlägst zuerst, aber der Gegner überlebt und schlägt zurück.
            return survival_if_hit

    # Szenario 2: Du bist langsamer
    elif my_speed < opponent_speed:
        # Du wirst immer zuerst getroffen.
        return survival_if_hit

    # Szenario 3: Speed Tie
    else: # my_speed == opponent_speed
        # Ergebnis, wenn du den Tie gewinnst (entspricht dem "schneller"-Szenario)
        survival_if_win_tie = 1.0 if can_i_ohko_opponent else survival_if_hit

        # Ergebnis, wenn du den Tie verlierst (entspricht dem "langsamer"-Szenario)
        survival_if_lose_tie = survival_if_hit

        # Der finale Score ist der Durchschnitt beider Ausgänge
        return 0.5 * survival_if_win_tie + 0.5 * survival_if_lose_tie

def main():
    print("Analyse Start")

    opponent_data = info_manager.get_trainer_team_from_trainer_name(global_infos.opponent_trainer_name)[0]
    opponent_team = opponent_data["team"]
    print(" ~ Fetched Opponent Data")
    for opp_pkm_data in opponent_team:
        print(f"   | {info_manager.get_name_from_id(opp_pkm_data['id'])} with {opp_pkm_data['moves']}")

    owned_list = global_infos.owned_pokemon_list
    print(" ~ Fetched Own Pokemon")

    # Wir berechnen beide Richtungen -> Fortschrittsbar entsprechend anpassen
    total_iterations = len(owned_list) * len(opponent_team) * 2

    # Dictionaries: nested mapping attacker_name -> defender_name -> raw_value
    raw_player_to_opponent = {}
    raw_opponent_to_player = {}
    # Neue Maps: attacker_name -> defender_name -> best_move_name
    best_move_player_to_opponent = {}
    best_move_opponent_to_player = {}
    print(" ~ Initialized Mapping Dictionaries")

    # Preload move-lists for all Pokémon (schneller repeated access)
    moves_cache = {}
    for own_pkm_name in owned_list:
        moves_cache[own_pkm_name] = info_manager.get_attacks_of_pokemon_as_list(own_pkm_name)
    print(" ~ Stored All Own Moves")
    opp_moves_cache = {}
    for opp_fight_data_pkm in opponent_team:
        opp_name = info_manager.get_name_from_id(opp_fight_data_pkm["id"])
        pkm_attack_list = [[]]
        for move_name in opp_fight_data_pkm["moves"]:
            pkm_attack_list[0].append(info_manager.get_attack_in_cache(move_name))
        opp_moves_cache[opp_name] = pkm_attack_list
    print(" ~ Stored All Opponent Moves")

    with tqdm(total=total_iterations, desc="Gesamtanalyse") as pbar:
        # Spieler -> Gegner
        for own_pkm_name in owned_list:
            own_pkm = info_manager.get_pokemon_in_cache(own_pkm_name)
            attacker_moves_list = moves_cache.get(own_pkm_name, [])
            raw_player_to_opponent.setdefault(own_pkm_name, {})
            best_move_player_to_opponent.setdefault(own_pkm_name, {})
            for opp_fight_data_pkm in opponent_team:
                opp_name = info_manager.get_name_from_id(opp_fight_data_pkm["id"])
                opp_pkm = info_manager.get_pokemon_in_cache(opp_name)

                best_raw, best_move = compute_best_damage_for_pair(own_pkm, own_pkm_name, opp_pkm, attacker_moves_list)
                raw_player_to_opponent[own_pkm_name][opp_name] = best_raw
                best_move_player_to_opponent[own_pkm_name][opp_name] = best_move

                pbar.update(1)

        # Gegner -> Spieler
        for opp_fight_data_pkm in opponent_team:
            opp_name = info_manager.get_name_from_id(opp_fight_data_pkm["id"])
            opp_pkm = info_manager.get_pokemon_in_cache(opp_name)
            attacker_moves_list = opp_moves_cache.get(opp_name, [])
            raw_opponent_to_player.setdefault(opp_name, {})
            best_move_opponent_to_player.setdefault(opp_name, {})
            for own_pkm_name in owned_list:
                own_pkm = info_manager.get_pokemon_in_cache(own_pkm_name)

                best_raw, best_move = compute_best_damage_for_pair(opp_pkm, opp_name, own_pkm, attacker_moves_list)
                raw_opponent_to_player[opp_name][own_pkm_name] = best_raw
                best_move_opponent_to_player[opp_name][own_pkm_name] = best_move

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
    print(" ~ Got min & max from raw values")

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

    print(" ~ Normalized Raw Values")

    # Ausgabe: (optional) print normalized damage scores in ähnlichem Format wie vorher
    # print("=== Normalized damage player -> opponent (0..1) ===")
    # for own_name, mapping in damage_player_to_opponent.items():
    #     for opp_name, score in mapping.items():
    #         print([own_name, opp_name, round(score, 4)])
    #
    # print("=== Normalized damage opponent -> player (0..1) ===")
    # for opp_name, mapping in damage_opponent_to_player.items():
    #     for own_name, score in mapping.items():
    #         print([opp_name, own_name, round(score, 4)])

    # ---------------------------
    # -> Compute CounterScore & Candidate Selection
    # ---------------------------

    # Precompute utility_scores and exposure (avg incoming damage)
    utility_scores = {}
    exposure_scores = {}  # exposure per own_pkm = avg damage_opponent_to_player over all opponents

    # Ensure move lists caches exist (moves_cache already built earlier)
    for own_name in owned_list:
        attacker_moves_list = moves_cache.get(own_name, [])
        utility_scores[own_name] = compute_utility_score_for_attacker(own_name, attacker_moves_list)

        # exposure: average of damage_opponent_to_player[*][own_name]
        incoming = []
        for opp_b in opponent_team:
            opp_name = info_manager.get_name_from_id(opp_b["id"])
            val = damage_opponent_to_player.get(opp_name, {}).get(own_name)
            if val is not None:
                incoming.append(val)
        exposure_scores[own_name] = (sum(incoming)/len(incoming)) if incoming else 0.0

    print(" ~ Calculated Utility and Exposure Scores")

    # Build raw counter scores (attacker -> defender)
    counter_raw = {}  # counter_raw[own][opp] = raw_score
    all_counter_raw_values = []

    for own_name in owned_list:
        counter_raw.setdefault(own_name, {})
        for opp_b in opponent_team:
            opp_name = info_manager.get_name_from_id(opp_b["id"])

            dmg_score = damage_player_to_opponent.get(own_name, {}).get(opp_name, 0.0)  # 0..1
            incoming_vs_own_from_opp = damage_opponent_to_player.get(opp_name, {}).get(own_name, 0.0)  # 0..1
            survival_estimate = 1.0 - incoming_vs_own_from_opp  # higher = better survive switch
            util = utility_scores.get(own_name, 0.0)
            exposure = exposure_scores.get(own_name, 0.0)

            raw_score = (global_infos.w_dmg * dmg_score) + (global_infos.w_surv * survival_estimate) + (global_infos.w_util * util) - (global_infos.w_expo * exposure)
            # keep raw
            counter_raw[own_name][opp_name] = raw_score
            all_counter_raw_values.append(raw_score)

    print(" ~ Calculated Counter Scores; Added Weights into Full Score")

    # Normalize counter_raw to 0..100 for readability
    counter_score = {}
    if all_counter_raw_values:
        cr_min = min(all_counter_raw_values)
        cr_max = max(all_counter_raw_values)
        if math.isclose(cr_min, cr_max):
            # edge: all equal -> 50
            for own_name, mapping in counter_raw.items():
                counter_score[own_name] = {opp: 50.0 for opp in mapping}
        else:
            span = cr_max - cr_min
            for own_name, mapping in counter_raw.items():
                counter_score.setdefault(own_name, {})
                for opp_name, raw_val in mapping.items():
                    norm01 = (raw_val - cr_min) / span
                    counter_score[own_name][opp_name] = round(norm01 * 100.0, 2)
    else:
        # nothing computed
        for own_name in owned_list:
            counter_score[own_name] = {info_manager.get_name_from_id(o["id"]): 50.0 for o in opponent_team}

    print(" ~ Normalized Counter Scores")

        # Candidate selection per opponent: rank own pokemon by counter_score(P,G)
    print("\n=== Top Counters pro Gegner (Top {}) ===".format(MAX_TOP_PER_OPP))
    for opp_b in opponent_team:
        opp_name = info_manager.get_name_from_id(opp_b["id"])
        # build list
        ranked = []
        for own_name in owned_list:
            score = counter_score.get(own_name, {}).get(opp_name, 0.0)
            # compute contribution breakdown for explanation
            dmg_score = damage_player_to_opponent.get(own_name, {}).get(opp_name, 0.0) # todo change to hits till ko
            incoming = damage_opponent_to_player.get(opp_name, {}).get(own_name, 0.0) # todo change to hits till ko
            survival = calculate_survival_score(info_manager.get_pokemon_in_cache(own_name), info_manager.get_pokemon_in_cache(opp_name), incoming, dmg_score, vmin, vmax)
            print(f"(opp) {opp_name} gegen {own_name} (own) - survival={get_farbigen_wert_string(survival)}")
            util = utility_scores.get(own_name, 0.0)
            exposure = exposure_scores.get(own_name, 0.0)

            # contributions (weighted)
            contribs = {
                "Schaden": global_infos.w_dmg * dmg_score,
                "Überlebens-Einschätzung": global_infos.w_surv * survival,
                "Utility": global_infos.w_util * util,
                "Exposure-Penalty": -global_infos.w_expo * exposure
            }

            # best moves (Names) — falls nicht vorhanden -> 'Unknown'
            own_best_move = best_move_player_to_opponent.get(own_name, {}).get(opp_name) or "Unknown"
            opp_best_move = best_move_opponent_to_player.get(opp_name, {}).get(own_name) or "Unknown"

            ranked.append((own_name, score, contribs, dmg_score, survival, util, exposure, own_best_move, opp_best_move))
        # sort desc by score
        ranked.sort(key=lambda x: x[1], reverse=True)

        print("\nGegner: {}".format(opp_name))
        for i, (own_name, score, contribs, dmg_score, survival, util, exposure, own_best_move, opp_best_move) in enumerate(ranked[:MAX_TOP_PER_OPP], start=1):
            # build top reason lines: pick top 2 positive contributors
            pos_contribs = [(k, v) for k, v in contribs.items() if v > 0]
            pos_contribs.sort(key=lambda x: x[1], reverse=True)
            top_reasons = []
            for k, v in pos_contribs[:2]:
                if k == "Schaden":
                    top_reasons.append(f"Hoher erwarteter Schaden (damage_score={get_farbigen_wert_string(dmg_score)})")
                elif k == "Überlebens-Einschätzung":
                    top_reasons.append(f"Gute Überlebenschance beim Switch (survival={get_farbigen_wert_string(survival)})")
                elif k == "Utility":
                    top_reasons.append(f"Nützliche Status/Recovery-Moves (utility={get_farbigen_wert_string(util)})")
            if exposure >= 0.4:
                top_reasons.append(f"Vorsicht: hohe Verwundbarkeit gegen restliches Team (exposure={get_farbigen_wert_string(exposure)})")

            print(f" {i}. {own_name} — Score: {score}")
            # Show best moves
            print(f"    - Top Move (eigener): {own_best_move} — gesch. Schaden : {((vmax - vmin) * dmg_score + vmin):.3f}")
            print(f"    - Top Move (Gegner): {opp_best_move} — gesch. incoming : {((vmax - vmin) * incoming + vmin):.3f}")
            for r in top_reasons:
                print(f"    - {r}")

    print("Analyse Ende")

if __name__ == "__main__":
    main()
