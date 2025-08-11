import json
import global_infos

def load_type_effectiveness_data(filename="information_storage/pokemon_type_effectiveness.json"):
    """
    Lädt die Typen-Effektivitätstabelle aus einer JSON-Datei.

    Args:
        filename (str): Der Pfad zur JSON-Datei.

    Returns:
        dict: Das geladene Dictionary mit der Typen-Effektivitätstabelle.
        None: Wenn die Datei nicht gefunden wurde, kein gültiges JSON enthält
              oder ein anderer Fehler auftritt.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            chart = json.load(f)
        return chart
    except FileNotFoundError:
        print(f"Fehler: Datei '{filename}' nicht gefunden.")
        return None
    except json.JSONDecodeError:
        print(f"Fehler: Datei '{filename}' enthält kein gültiges JSON.")
        return None
    except Exception as e:
        print(f"Ein unerwarteter Fehler beim Lesen der Datei ist aufgetreten: {e}")
        return None

def get_effectiveness_from_type_chart(type_chart, attack_type, defense_types):
    if not isinstance(defense_types, (list, tuple)) or not (1 <= len(defense_types) <= 2):
        raise ValueError(f"Ungültige defense_types: {defense_types}")

    try:
        attacker_map = type_chart[attack_type]
    except KeyError:
        raise ValueError(f"Ungültiger Angriffstyp: {attack_type}")

    if len(defense_types) == 1:
        key = f"{defense_types[0]}, None"
    else:
        key = ", ".join(sorted(defense_types))

    try:
        return float(attacker_map[key])
    except KeyError:
        raise ValueError(f"Typ-Kombination '{key}' nicht gefunden für Angriffstyp '{attack_type}'")
    except (TypeError, ValueError):
        raise ValueError(f"Ungültiger Effektivitätswert für Schlüssel '{key}'")

def get_effectiveness(attack_type, defense_types):
    return float(get_effectiveness_from_type_chart(load_type_effectiveness_data(), attack_type, defense_types))

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

    if len(defense_types) == 2 and defense_types[0] == defense_types[1]:
        defense_types = [defense_types[0]]

    result = {}
    for attack_type in global_infos.pokemon_types:
        eff = get_effectiveness_from_type_chart(type_chart, attack_type, defense_types)
        if eff is None:
            continue

        if filter_mode == "weakness" and eff <= 1.0:
            continue
        elif filter_mode == "resistance" and eff >= 1.0:
            continue

        result[attack_type] = eff

    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))  # Höchste Effektivität zuerst
