import json

def load_type_chart(filename="pokemon_type_chart.json"):
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
        print(f"Typen-Effektivitätstabelle erfolgreich aus '{filename}' geladen.")
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

def get_effectiveness(type_chart, attack_type, defense_types):
    """
    Ermittelt die Effektivität einer Attacke gegen einen oder zwei Verteidiger-Typen.

    Behandelt automatisch die korrekte Schlüsselbildung für Einzel- und Doppeltypen
    (Doppeltypen werden alphabetisch sortiert für den Lookup).

    Args:
        type_chart (dict): Die geladene Typen-Effektivitätstabelle.
        attack_type (str): Der Typ der angreifenden Attacke (z.B. "Feuer").
        defense_types (list[str]): Eine Liste mit einem oder zwei Verteidiger-Typen
                                   (z.B. ["Pflanze"] oder ["Pflanze", "Gift"]).

    Returns:
        float: Der Effektivitätsmultiplikator (z.B. 0.0, 0.5, 1.0, 2.0).
        None: Wenn die Eingabe ungültig ist (z.B. falsche Anzahl an Typen,
              ungültiger Angriffstyp) oder die Kombination nicht gefunden wurde.
              Letzteres sollte bei korrekt generierter JSON nicht passieren.
    """
    if not type_chart:
        print("Fehler: Type Chart wurde nicht korrekt geladen.")
        return None

    if not isinstance(defense_types, (list, tuple)) or not 1 <= len(defense_types) <= 2:
        print(f"Fehler: defense_types muss eine Liste/Tuple mit 1 oder 2 Typen sein, erhalten: {defense_types}")
        return None

    # Hole das Unter-Dictionary für den Angriffstyp (sicher mit .get)
    attacker_effectiveness_map = type_chart.get(attack_type)
    if not attacker_effectiveness_map:
        print(f"Fehler: Angriffstyp '{attack_type}' nicht in der Type Chart gefunden.")
        return None

    # Baue den Schlüssel für die Abfrage basierend auf der Anzahl der Verteidiger-Typen
    lookup_key = None
    if len(defense_types) == 1:
        # Einzeltyp-Verteidiger: Format "Typ, None"
        lookup_key = f"{defense_types[0]}, None"
    elif len(defense_types) == 2:
        # Doppeltyp-Verteidiger: Sortiere alphabetisch für das Format "TypA, TypB"
        type1, type2 = defense_types[0], defense_types[1]
        # Stelle sicher, dass die Typen gültig sind (optional, aber gute Praxis)
        # if type1 not in type_chart or type2 not in type_chart: # Prüft nur, ob sie als Angreifer existieren
        #     print(f"Warnung: Einer der Verteidiger-Typen '{type1}'/'{type2}' ist möglicherweise ungültig.")

        sorted_types = sorted((type1, type2))
        lookup_key = f"{sorted_types[0]}, {sorted_types[1]}"

    # Mache den Lookup im Dictionary des Angreifers
    effectiveness = attacker_effectiveness_map.get(lookup_key)

    if effectiveness is None:
        # Dieser Fall sollte eigentlich nicht auftreten, wenn die JSON korrekt ist
        # und die Typnamen übereinstimmen. Wir geben trotzdem eine Meldung aus.
        print(f"Warnung: Schlüssel '{lookup_key}' für Angreifer '{attack_type}' nicht gefunden.")
        # Hier *könnte* man einen Fallback einbauen, aber bei korrekter JSON ist er unnötig.
        # Die Logik oben stellt sicher, dass immer der korrekte, sortierte Schlüssel verwendet wird.
        return None # Oder vielleicht 1.0 als Standard zurückgeben? None ist klarer bei Fehlern.

    return effectiveness

type_chart = load_type_chart()

pokemon_typen = [
    "Normal", "Feuer", "Wasser", "Elektro", "Pflanze", "Eis",
    "Kampf", "Gift", "Boden", "Flug", "Psycho", "Käfer",
    "Gestein", "Geist", "Drache", "Unlicht", "Stahl", "Fee"
]

defensive_types = ['Boden', 'Geist']

print(f"\nSchwächen für Typ {str(defensive_types)}")

for typ in pokemon_typen:
    effectiveness = get_effectiveness(type_chart, typ, defensive_types)
    if effectiveness <= 1:
        continue
    print(typ + ": " + str(effectiveness))

print(f"\nStärken für Typ {str(defensive_types)}")

for typ in pokemon_typen:
    effectiveness = get_effectiveness(type_chart, typ, defensive_types)
    if effectiveness >= 1:
        continue
    print(typ + ": " + str(effectiveness))


