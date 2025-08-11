import global_infos
import information_manager
import type_effectiveness
from tqdm import tqdm # Importiere die tqdm-Bibliothek
import math

# Hilfssets / heuristics für utility detection (Deutsch/Englisch gemischt, erweiterbar)
RECOVERY_KEYWORDS = ["Erholung", "Genesung", "Erholung", "Recover", "Rest", "Ruheort", "Heil", "Regener"]
# Status moves zählen wir, wenn die Move-Kategorie "Status" ist (so vorhanden)
MAX_TOP_PER_OPP = 3

# Liste mit heilenden Moves (kleingeschrieben für einfache Vergleiche)
HEALING_MOVES = {
    "morgengrauen","mondschein","genesung","ruheort","synthese","heilbefehl","tagedieb",
    "sandsammler","lunargebet","weichei","milchgetränk","läuterung","erholung","verzehrer",
    "heilwoge","florakur","pollenknödel","lebentropfen","dschungelheilung","giga-lichtblick",
    "wunschtraum","lunartanz","heilopfer","wasserring","verwurzler","egelsamen","vitalsegen",
    "vitalglocke","heilung","aromakur","mutschub"  # "Heilblockade" ist kein Heil-Move, daher nicht enthalten
}

# Hinweis: falls es unterschiedliche Schreibweisen in deinem Cache gibt (z. B. 'Giga-Lichtblick' vs 'Giga Lichtblick'),
# kannst du noch zusätzliche Varianten hinzufügen oder beim Vergleich non-alphanumerische Zeichen entfernen.


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
            if move_name_norm in HEALING_MOVES:
                has_recovery = True

            # Status detection: prefer move_cache Kategorie, fallback auf move_meta
            move_cache = information_manager.get_attack_in_cache(move_name) if move_name else None
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
            opp_name = information_manager.get_name_from_id(opp_b["id"])
            val = damage_opponent_to_player.get(opp_name, {}).get(own_name)
            if val is not None:
                incoming.append(val)
        exposure_scores[own_name] = (sum(incoming)/len(incoming)) if incoming else 0.0

    # Weights (tweakable)
    w_dmg = 3.0
    w_surv = 2.0
    w_util = 1.0
    w_expo = 1.5

    # Build raw counter scores (attacker -> defender)
    counter_raw = {}  # counter_raw[own][opp] = raw_score
    all_counter_raw_values = []

    for own_name in owned_list:
        counter_raw.setdefault(own_name, {})
        for opp_b in opponent_team:
            opp_name = information_manager.get_name_from_id(opp_b["id"])

            dmg_score = damage_player_to_opponent.get(own_name, {}).get(opp_name, 0.0)  # 0..1
            incoming_vs_own_from_opp = damage_opponent_to_player.get(opp_name, {}).get(own_name, 0.0)  # 0..1
            survival_estimate = 1.0 - incoming_vs_own_from_opp  # higher = better survive switch
            util = utility_scores.get(own_name, 0.0)
            exposure = exposure_scores.get(own_name, 0.0)

            raw_score = (w_dmg * dmg_score) + (w_surv * survival_estimate) + (w_util * util) - (w_expo * exposure)
            # keep raw
            counter_raw[own_name][opp_name] = raw_score
            all_counter_raw_values.append(raw_score)

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
            counter_score[own_name] = {information_manager.get_name_from_id(o["id"]): 50.0 for o in opponent_team}

    # Candidate selection per opponent: rank own pokemon by counter_score(P,G)
    print("\n=== Top Counters pro Gegner (Top {}) ===".format(MAX_TOP_PER_OPP))
    for opp_b in opponent_team:
        opp_name = information_manager.get_name_from_id(opp_b["id"])
        # build list
        ranked = []
        for own_name in owned_list:
            score = counter_score.get(own_name, {}).get(opp_name, 0.0)
            # compute contribution breakdown for explanation
            dmg_score = damage_player_to_opponent.get(own_name, {}).get(opp_name, 0.0)
            incoming = damage_opponent_to_player.get(opp_name, {}).get(own_name, 0.0)
            survival = 1.0 - incoming
            util = utility_scores.get(own_name, 0.0)
            exposure = exposure_scores.get(own_name, 0.0)

            # contributions (weighted)
            contribs = {
                "Schaden": w_dmg * dmg_score,
                "Überlebens-Einschätzung": w_surv * survival,
                "Utility": w_util * util,
                "Exposure-Penalty": -w_expo * exposure
            }
            ranked.append((own_name, score, contribs, dmg_score, survival, util, exposure))
        # sort desc by score
        ranked.sort(key=lambda x: x[1], reverse=True)

        print("\nGegner: {}".format(opp_name))
        for i, (own_name, score, contribs, dmg_score, survival, util, exposure) in enumerate(ranked[:MAX_TOP_PER_OPP], start=1):
            # build top reason lines: pick top 2 positive contributors
            pos_contribs = [(k, v) for k, v in contribs.items() if v > 0]
            pos_contribs.sort(key=lambda x: x[1], reverse=True)
            top_reasons = []
            for k, v in pos_contribs[:2]:
                # make human friendly
                if k == "Schaden":
                    top_reasons.append(f"Hoher erwarteter Schaden (damage_score={dmg_score:.3f})")
                elif k == "Überlebens-Einschätzung":
                    top_reasons.append(f"Gute Überlebenschance beim Switch (survival={survival:.3f})")
                elif k == "Utility":
                    top_reasons.append(f"Nützliche Status/Recovery-Moves (utility={util:.2f})")
            # also add primary risk if exposure large
            if exposure >= 0.4:
                top_reasons.append(f"Vorsicht: hohe Verwundbarkeit gegen restliches Team (exposure={exposure:.2f})")

            print(f" {i}. {own_name} — Score: {score}")
            for r in top_reasons:
                print(f"    - {r}")

    # Ende Counter/Selection Block

    print("Analyse Ende")

if __name__ == "__main__":
    main()
