import json

def load_type_chart(filename="pokemon_type_chart.json"):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            chart = json.load(f)
        return chart
    except Exception as e:
        print(f"Fehler beim Laden der Type Chart: {e}")
        return None

def get_effectiveness(type_chart, attack_type, defense_types):
    if not type_chart or attack_type not in type_chart:
        return None

    if not isinstance(defense_types, (list, tuple)) or not (1 <= len(defense_types) <= 2):
        return None

    attacker_map = type_chart[attack_type]

    if len(defense_types) == 1:
        key = f"{defense_types[0]}, None"
    else:
        sorted_types = sorted(defense_types)
        key = f"{sorted_types[0]}, {sorted_types[1]}"

    return attacker_map.get(key)

def get_type_matchups(type_chart, defense_types, filter_mode=None):
    """
    Gibt die Effektivitäten aller Angriffstypen gegen einen Verteidigertyp (Mono oder Duo) zurück.

    Args:
        type_chart (dict): Geladene Type Chart.
        defense_types (list[str]): Ein oder zwei Typen des Verteidigers.
        filter_mode (str|None): Optional: "weakness", "resistance" oder None (alles zeigen).

    Returns:
        dict[str, float]: Alle Typen mit zugehöriger Effektivität gegen den Verteidigertyp.
    """
    pokemon_types = [
        "Normal", "Feuer", "Wasser", "Elektro", "Pflanze", "Eis",
        "Kampf", "Gift", "Boden", "Flug", "Psycho", "Käfer",
        "Gestein", "Geist", "Drache", "Unlicht", "Stahl", "Fee"
    ]

    result = {}
    for attack_type in pokemon_types:
        eff = get_effectiveness(type_chart, attack_type, defense_types)
        if eff is None:
            continue

        if filter_mode == "weakness" and eff <= 1.0:
            continue
        elif filter_mode == "resistance" and eff >= 1.0:
            continue

        result[attack_type] = eff

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))  # Höchste Effektivität zuerst
